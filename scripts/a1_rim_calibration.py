#!/usr/bin/env python3
"""Isolated, training-only calibration of the rim shot-result matchup response."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize_scalar
from scipy.special import expit, logit

from scripts import nodes


def _inputs(probabilities: np.ndarray, matchup: np.ndarray, zones: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    probs = np.asarray(probabilities, dtype=float)
    values = np.asarray(matchup, dtype=float)
    zone = np.asarray(zones)
    if probs.ndim != 2 or probs.shape[1] != 3 or values.shape != (len(probs),) or zone.shape != (len(probs),):
        raise ValueError('shot probabilities, matchup profiles and zones must align')
    if (not np.isfinite(probs).all() or (probs <= 0).any() or (probs >= 1).any()
            or not np.allclose(probs.sum(axis=1), 1.0, rtol=0, atol=1e-10)):
        raise ValueError('shot-result probabilities must be finite, positive and sum to one')
    if (np.isinf(values).any() or ((values < 0) | (values > 1)).any()
            or not np.isin(zone, nodes.ZONES).all()):
        raise ValueError('matchup profiles or shot zones are invalid')
    made = probs[:, 1:].sum(axis=1)
    if ((made <= 0) | (made >= 1)).any():
        raise ValueError('shot make probabilities must lie strictly between zero and one')
    return probs, values, zone


def _intercept(offset: np.ndarray, target: float) -> float:
    target_logit = float(logit(target))
    low = target_logit - float(offset.max()) - 1.0
    high = target_logit - float(offset.min()) + 1.0
    root = brentq(lambda value: float(expit(offset + value).mean() - target), low, high, xtol=1e-12)
    if isinstance(root, tuple):
        raise TypeError('rim mean-preserving root unexpectedly returned diagnostics')
    return float(root)


def fit(probabilities: np.ndarray, matchup: np.ndarray, zones: np.ndarray, outcomes: np.ndarray,
        dates: np.ndarray, train_through: str) -> dict:
    probs, values, zone = _inputs(probabilities, matchup, zones)
    result = np.asarray(outcomes)
    day = pd.to_datetime(pd.Series(np.asarray(dates)), errors='raise')
    cutoff = pd.to_datetime(train_through, errors='raise')
    if (result.shape != (len(probs),) or len(day) != len(probs) or day.isna().any()
            or (day > cutoff).any() or not np.isin(result, [0, 1, 2]).all()):
        raise ValueError('calibration outcomes or strictly pre-validation dates are invalid')
    eligible = (zone == 'rim') & np.isfinite(values)
    if eligible.sum() < 2:
        raise ValueError('too few known rim matchup observations to fit a calibration')
    x = values[eligible]
    if np.ptp(x) <= np.finfo(float).eps:
        raise ValueError('rim matchup profiles have no variation')
    mean = float(x.mean())
    centered = x - mean
    base = probs[eligible, 1:].sum(axis=1)
    target = float(base.mean())
    raw = logit(base)
    made = (result[eligible] != 0).astype(float)
    if made.sum() == 0 or made.sum() == len(made):
        raise ValueError('rim calibration needs both makes and misses')

    def objective(slope: float) -> float:
        offset = raw + slope * centered
        z = offset + _intercept(offset, target)
        return float(np.mean(np.logaddexp(0.0, z) - made * z))

    fitted = minimize_scalar(objective, method='brent')
    if not fitted.success or not np.isfinite(fitted.x) or not np.isfinite(fitted.fun):
        raise ValueError(f'rim calibration did not converge: {fitted.message}')
    slope = float(fitted.x)
    intercept = _intercept(raw + slope * centered, target)
    calibrated = expit(raw + slope * centered + intercept)
    if ((calibrated <= 0) | (calibrated >= 1)).any():
        raise ValueError('rim calibration produced degenerate training probabilities')
    if not np.isclose(calibrated.mean(), target, rtol=0, atol=1e-12):
        raise ValueError('rim calibration did not preserve the training mean')
    return {'train_through': str(cutoff.date()), 'latest_training_date': str(day.max().date()),
            'training_rows': len(probs), 'known_rim_rows': int(eligible.sum()), 'center': mean,
            'slope': slope, 'intercept': intercept, 'baseline_mean': target,
            'calibrated_mean': float(calibrated.mean()), 'objective': float(fitted.fun)}


def apply(probabilities: np.ndarray, matchup: np.ndarray, zones: np.ndarray, calibration: dict) -> np.ndarray:
    probs, values, zone = _inputs(probabilities, matchup, zones)
    parameters = np.asarray([calibration[k] for k in ('center', 'slope', 'intercept')], dtype=float)
    if not np.isfinite(parameters).all():
        raise ValueError('rim calibration parameters must be finite')
    eligible = (zone == 'rim') & np.isfinite(values)
    out = probs.copy()
    base = probs[eligible, 1:].sum(axis=1)
    adjusted = expit(logit(base) + parameters[2] + parameters[1] * (values[eligible] - parameters[0]))
    if ((adjusted <= 0) | (adjusted >= 1)).any():
        raise ValueError('rim calibration produced degenerate shot probabilities')
    out[eligible, 0] = 1 - adjusted
    out[eligible, 1:] = probs[eligible, 1:] * (adjusted / base)[:, None]
    if not np.allclose(out.sum(axis=1), 1.0, rtol=0, atol=1e-10):
        raise ValueError('calibrated shot probabilities do not sum to one')
    return out
