"""Calibration and discrimination metrics for the recovery probability model."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(slots=True)
class CalibrationBin:
    lower: float
    upper: float
    count: int
    predicted: float
    observed: float


@dataclass(slots=True)
class ModelMetrics:
    samples: int
    positives: int
    brier_score: float
    log_loss: float
    roc_auc: float
    #: Mean absolute gap between predicted and observed rates across bins.
    calibration_error: float
    base_rate: float
    bins: list[CalibrationBin]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["bins"] = [asdict(b) if not isinstance(b, dict) else b for b in self.bins]
        return payload


def brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(np.mean((y_prob - y_true) ** 2))


def log_loss(y_true: np.ndarray, y_prob: np.ndarray, eps: float = 1e-12) -> float:
    p = np.clip(y_prob, eps, 1 - eps)
    return float(-np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p)))


def roc_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Rank-based AUC. Returns 0.5 when only one class is present."""
    positives = y_true == 1
    n_pos, n_neg = int(positives.sum()), int((~positives).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5
    order = np.argsort(y_prob, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(y_prob) + 1)
    # Average ranks within ties so identical scores do not inflate the statistic.
    sorted_probs = y_prob[order]
    start = 0
    for idx in range(1, len(sorted_probs) + 1):
        if idx == len(sorted_probs) or sorted_probs[idx] != sorted_probs[start]:
            if idx - start > 1:
                ranks[order[start:idx]] = ranks[order[start:idx]].mean()
            start = idx
    return float((ranks[positives].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def calibration_bins(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> list[CalibrationBin]:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins: list[CalibrationBin] = []
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        mask = (y_prob >= lower) & (y_prob < upper if upper < 1.0 else y_prob <= upper)
        count = int(mask.sum())
        if count == 0:
            continue
        bins.append(
            CalibrationBin(
                lower=round(float(lower), 3),
                upper=round(float(upper), 3),
                count=count,
                predicted=round(float(y_prob[mask].mean()), 4),
                observed=round(float(y_true[mask].mean()), 4),
            )
        )
    return bins


def evaluate(y_true: np.ndarray, y_prob: np.ndarray) -> ModelMetrics:
    bins = calibration_bins(y_true, y_prob)
    weighted_gap = sum(abs(b.predicted - b.observed) * b.count for b in bins)
    total = sum(b.count for b in bins) or 1
    return ModelMetrics(
        samples=int(len(y_true)),
        positives=int(y_true.sum()),
        brier_score=round(brier_score(y_true, y_prob), 5),
        log_loss=round(log_loss(y_true, y_prob), 5),
        roc_auc=round(roc_auc(y_true, y_prob), 4),
        calibration_error=round(weighted_gap / total, 5),
        base_rate=round(float(y_true.mean()), 4),
        bins=bins,
    )
