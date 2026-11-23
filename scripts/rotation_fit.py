"""Independent per-world version of the existing D29 offset fitter; opt-in until qualified."""
import numpy as np


def independent(curves, targets, settings):
    curves, targets = np.asarray(curves), np.asarray(targets)
    if curves.ndim != 3 or targets.shape != curves.shape[:2] or curves.shape[1] < 5 or not np.isfinite(curves).all() or not np.isfinite(targets).all():
        raise ValueError('finite per-world rotation curves and targets required')
    worlds, players, bins = curves.shape
    offset = np.zeros((worlds, players))
    best = np.empty((worlds, 5, bins), np.int64)
    best_error = np.full(worlds, np.inf)
    active = np.arange(worlds)
    for iteration in range(settings['iters']):
        if not len(active):
            break
        score = curves[active] + offset[active, :, None]
        top = np.argpartition(-score, 4, axis=1)[:, :5]
        on = np.zeros((len(active), players, bins), bool)
        np.put_along_axis(on, top, True, axis=1)
        error = targets[active] - on.sum(2) * (settings['bin'] / 60)
        magnitude = np.abs(error).max(1)
        improved = magnitude < best_error[active]
        best[active[improved]] = top[improved]
        best_error[active[improved]] = magnitude[improved]
        offset[active] += (1. / 48) * error * (.96 ** iteration)
        active = active[magnitude > settings['tol']]
    if not np.isfinite(best_error).all():
        raise ValueError('rotation fit produced no candidate')
    return best
