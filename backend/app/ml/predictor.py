"""Recovery probability prediction.

The model is trained with the intervention as an input column, so substituting the
action and re-scoring the same row yields the counterfactual set Revyn needs:
``P(recover | action)`` for every candidate plus ``P(recover | do nothing)``, which is
the organic baseline the incremental ledger is measured against.

A calibrated gradient-boosted model is used when an artifact is present; otherwise the
deterministic fallback keeps every downstream engine working.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.core.constants import ActionType, RootCause
from app.core.logging import get_logger
from app.data.catalog import affinity, cause_profile, intervention

log = get_logger(__name__)

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "recovery_model.joblib"
METADATA_PATH = ARTIFACT_DIR / "model_metadata.json"

Features = dict[str, float | str]


@dataclass(slots=True)
class ActionProbabilities:
    organic: float
    per_action: dict[ActionType, float]

    def uplift(self, action: ActionType) -> float:
        return max(self.per_action.get(action, self.organic) - self.organic, 0.0)


class Predictor(Protocol):
    version: str

    def score(self, features: Features, actions: list[ActionType]) -> ActionProbabilities: ...


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class HeuristicPredictor:
    """Closed-form fallback.

    Organic recovery and intervention lift are composed rather than added, so an
    intervention can never be scored below the do-nothing baseline.
    """

    version = "heuristic-v1"

    def score(self, features: Features, actions: list[ActionType]) -> ActionProbabilities:
        organic = self._organic(features)
        per_action = {ActionType.DO_NOTHING: organic}
        for action in actions:
            if action is ActionType.DO_NOTHING:
                continue
            lift = self._lift(features, action)
            per_action[action] = _clamp(organic + (1.0 - organic) * lift, 0.01, 0.97)
        return ActionProbabilities(organic=organic, per_action=per_action)

    @staticmethod
    def _customer_factor(features: Features) -> float:
        return _clamp(
            0.60
            + 0.55 * float(features.get("prev_success_rate", 0.5))
            + 0.35 * float(features.get("historical_recovery_rate", 0.2)),
            0.5,
            1.55,
        )

    def _organic(self, features: Features) -> float:
        retry_decay = 0.82 ** float(features.get("retry_count", 0.0))
        base = 0.10 * float(features.get("organic_multiplier", 1.0))
        return _clamp(base * self._customer_factor(features) * retry_decay, 0.01, 0.55)

    def _lift(self, features: Features, action: ActionType) -> float:
        spec = intervention(action)
        cause = RootCause(str(features.get("root_cause", RootCause.UNKNOWN)))
        value_shape = 1.0 / (1.0 + 0.09 * math.log1p(float(features.get("amount_vs_aov", 1.0))))
        fatigue = 0.90 ** float(features.get("prior_contacts", 0.0))
        lift = spec.base_success * affinity(cause, action) * value_shape * fatigue
        lift *= _clamp(self._customer_factor(features), 0.6, 1.35)
        if features.get("degradation_active") and action is ActionType.RETRY_PAYMENT:
            lift *= 0.35
        if action is ActionType.RETRY_PAYMENT and not cause_profile(cause).retryable:
            lift *= 0.30
        return _clamp(lift, 0.0, 0.92)


class CalibratedModelPredictor:
    """Wraps the persisted sklearn pipeline and the vectoriser it was fitted with."""

    def __init__(self, pipeline: Any, metadata: dict[str, Any]) -> None:
        self._pipeline = pipeline
        self.metadata = metadata
        self.version = metadata.get("version", "gbdt")
        self._fallback = HeuristicPredictor()

    def score(self, features: Features, actions: list[ActionType]) -> ActionProbabilities:
        from app.engines.features import with_action

        candidates = [
            ActionType.DO_NOTHING,
            *[a for a in actions if a is not ActionType.DO_NOTHING],
        ]
        rows = [with_action(features, action) for action in candidates]
        try:
            probs = self._pipeline.predict_proba(rows)[:, 1]
        except Exception as exc:  # pragma: no cover - artifact/feature drift
            log.warning("predictor.inference_failed", extra={"error": str(exc)})
            return self._fallback.score(features, actions)

        organic = _clamp(float(probs[0]), 0.01, 0.95)
        per_action = {ActionType.DO_NOTHING: organic}
        for action, prob in zip(candidates[1:], probs[1:], strict=True):
            # An intervention cannot do worse than leaving the customer alone.
            per_action[action] = _clamp(max(float(prob), organic), 0.01, 0.97)
        return ActionProbabilities(organic=organic, per_action=per_action)


_predictor: Predictor | None = None


def load_predictor() -> Predictor:
    if not MODEL_PATH.exists():
        log.info("predictor.using_heuristic", extra={"reason": "artifact_missing"})
        return HeuristicPredictor()
    try:
        import joblib

        pipeline = joblib.load(MODEL_PATH)
        metadata = json.loads(METADATA_PATH.read_text()) if METADATA_PATH.exists() else {}
        log.info("predictor.loaded", extra={"version": metadata.get("version")})
        return CalibratedModelPredictor(pipeline, metadata)
    except Exception as exc:  # pragma: no cover - corrupt or incompatible artifact
        log.warning("predictor.load_failed", extra={"error": str(exc)})
        return HeuristicPredictor()


def get_predictor() -> Predictor:
    global _predictor
    if _predictor is None:
        _predictor = load_predictor()
    return _predictor


def reload_predictor() -> Predictor:
    global _predictor
    _predictor = load_predictor()
    return _predictor


def model_metadata() -> dict[str, Any]:
    predictor = get_predictor()
    if isinstance(predictor, CalibratedModelPredictor):
        return {"trained": True, **predictor.metadata}
    return {"trained": False, "version": predictor.version}
