"""Fits and calibrates the recovery probability model from resolved history."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.core.config import settings
from app.core.constants import ActionType, EventStatus
from app.core.logging import get_logger
from app.engines.features import FeatureContext, build_features, with_action
from app.ml.metrics import ModelMetrics, evaluate
from app.ml.predictor import ARTIFACT_DIR, METADATA_PATH, MODEL_PATH, reload_predictor
from app.models.event import RevenueEvent

log = get_logger(__name__)

MIN_TRAINING_ROWS = 400


async def load_training_rows(session: AsyncSession) -> list[tuple[dict[str, Any], int]]:
    """Resolved history: features with the observed intervention, labelled by outcome."""
    stmt = select(RevenueEvent).where(
        RevenueEvent.is_training.is_(True),
        RevenueEvent.status.in_([EventStatus.RECOVERED, EventStatus.LOST]),
        RevenueEvent.applied_action.is_not(None),
    )
    events = (await session.execute(stmt)).unique().scalars().all()
    rows: list[tuple[dict[str, Any], int]] = []
    for event in events:
        context = FeatureContext(
            degradation_active=bool(event.diagnosis.get("degradation_active", False)),
            degradation_ratio=float(event.diagnosis.get("degradation_ratio", 1.0)),
        )
        features = with_action(
            build_features(event, event.customer, context), ActionType(event.applied_action)
        )
        rows.append((features, 1 if event.status == EventStatus.RECOVERED else 0))
    return rows


def _build_pipeline():
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.pipeline import Pipeline

    return Pipeline(
        [
            ("vectorizer", DictVectorizer(sparse=False)),
            (
                "classifier",
                CalibratedClassifierCV(
                    HistGradientBoostingClassifier(
                        max_depth=6,
                        max_iter=260,
                        learning_rate=0.07,
                        min_samples_leaf=25,
                        l2_regularization=0.6,
                        random_state=settings.seed,
                    ),
                    method="isotonic",
                    cv=4,
                ),
            ),
        ]
    )


def train_from_rows(
    rows: list[tuple[dict[str, Any], int]],
) -> tuple[Any, ModelMetrics, ModelMetrics]:
    """Fit on a stratified 80% split and report train/holdout calibration."""
    rng = np.random.default_rng(settings.seed)
    labels = np.array([label for _, label in rows])
    indices = np.arange(len(rows))

    holdout_mask = np.zeros(len(rows), dtype=bool)
    for label_value in (0, 1):
        label_idx = indices[labels == label_value]
        rng.shuffle(label_idx)
        holdout_mask[label_idx[: max(int(len(label_idx) * 0.2), 1)]] = True

    x_train = [rows[i][0] for i in indices[~holdout_mask]]
    y_train = labels[~holdout_mask]
    x_test = [rows[i][0] for i in indices[holdout_mask]]
    y_test = labels[holdout_mask]

    pipeline = _build_pipeline()
    pipeline.fit(x_train, y_train)

    train_metrics = evaluate(y_train.astype(float), pipeline.predict_proba(x_train)[:, 1])
    holdout_metrics = evaluate(y_test.astype(float), pipeline.predict_proba(x_test)[:, 1])
    return pipeline, train_metrics, holdout_metrics


def persist(pipeline: Any, holdout: ModelMetrics, train: ModelMetrics, rows: int) -> dict[str, Any]:
    import joblib

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    metadata = {
        "version": f"gbdt-isotonic-{utcnow():%Y%m%d%H%M}",
        "algorithm": "HistGradientBoosting + isotonic calibration",
        "trained_at": utcnow().isoformat(),
        "training_rows": rows,
        "holdout": holdout.to_dict(),
        "train": train.to_dict(),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))
    return metadata


async def train(session: AsyncSession) -> dict[str, Any]:
    rows = await load_training_rows(session)
    if len(rows) < MIN_TRAINING_ROWS:
        log.warning("train.insufficient_rows", extra={"rows": len(rows)})
        return {"trained": False, "reason": "insufficient_training_rows", "rows": len(rows)}

    pipeline, train_metrics, holdout_metrics = train_from_rows(rows)
    metadata = persist(pipeline, holdout_metrics, train_metrics, len(rows))
    reload_predictor()
    log.info(
        "train.completed",
        extra={
            "rows": len(rows),
            "brier": holdout_metrics.brier_score,
            "auc": holdout_metrics.roc_auc,
        },
    )
    return {"trained": True, **metadata}


def artifact_age_hours() -> float | None:
    if not MODEL_PATH.exists():
        return None
    modified = datetime.fromtimestamp(MODEL_PATH.stat().st_mtime, tz=utcnow().tzinfo)
    return (utcnow() - modified).total_seconds() / 3600.0
