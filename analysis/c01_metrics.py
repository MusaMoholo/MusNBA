"""Common C01 empirical scoring, game-paired uncertainty and support tables."""
from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.c01_core import ContractError, score


def crps(x, y):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    if not n or not np.isfinite(x).all() or not np.isfinite(y):
        raise ContractError("invalid independent score input")
    # Order-statistic identity, independent of core.score's integrated-CDF code.
    return float(np.abs(x - y).mean() - np.dot(2 * np.arange(1, n + 1) - n - 1, x) / n**2)


def scalar_record(x, y):
    r = score(x, y)
    if not r["supported"]:
        return {"supported": False}
    q05, q95 = np.quantile(x, [.05, .95], method="inverted_cdf")
    out = {k: r[k] for k in ("crps", "mean", "bias", "absolute_error")}
    out.update({"supported": True, "truth": float(y), "rank_lo": r["rank_bounds"][0], "rank_hi": r["rank_bounds"][1],
                "tail_low": float(y < q05), "tail_high": float(y > q95),
                "crps_half1": crps(x[:500], y), "crps_half2": crps(x[500:], y)})
    for level in (.5, .8, .95):
        interval = r["intervals"][str(level)]
        for field in ("lo", "hi", "width", "covered"):
            out[f"{field}{round(100*level)}"] = float(interval[field])
    return out


def energy(samples, truth, shifts=range(1, 33)):
    x, y = np.asarray(samples, float), np.asarray(truth, float)
    if x.ndim != 2 or x.shape[1] != 2 or y.shape != (2,) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ContractError("invalid joint samples")
    first = np.linalg.norm(x - y, axis=1).mean()
    second = np.mean([np.linalg.norm(x - np.roll(x, s, axis=0), axis=1).mean() for s in shifts])
    return float(first - second / 2)


def energy_reference(samples, truth):
    x = np.asarray(samples, float)
    return float(np.linalg.norm(x - truth, axis=1).mean() - np.linalg.norm(x[:, None, :] - x[None, :, :], axis=2).mean() / 2)


def joint_record(x, truth):
    wins, ties = int((x[:, 0] > x[:, 1]).sum()), int((x[:, 0] == x[:, 1]).sum())
    p = (wins + .5 * ties) / len(x)
    observed = float(truth[0] > truth[1])
    prob = p if observed else 1 - p
    smooth = (wins + .5 * ties + .5) / (len(x) + 1)
    return {"p_home": float(p), "home_won": observed, "win_brier": float((p - observed)**2),
            "win_log_loss": float(-np.log(prob)) if prob else None, "win_log_loss_infinite": not bool(prob),
            "win_log_loss_smoothed": float(-np.log(smooth if observed else 1 - smooth)),
            "ties_probability": ties / len(x), "negative_score_probability": float((x < 0).any(axis=1).mean()),
            "energy": energy(x, truth), "energy_second_shifts": energy(x, truth, range(33, 65)),
            "covariance": float(np.cov(x.T, ddof=0)[0, 1]), "home_sd": float(x[:, 0].std()), "away_sd": float(x[:, 1].std())}


def paired_frame(reference, candidate, metric="crps"):
    keys = ["game_id", "entity", "stat", "player", "side"]
    if reference.duplicated(keys).any() or candidate.duplicated(keys).any():
        raise ContractError("duplicate common scoring key")
    a, b = reference.set_index(keys).sort_index(), candidate.set_index(keys).sort_index()
    if not a.index.equals(b.index) or not np.array_equal(a.truth.to_numpy(), b.truth.to_numpy(), equal_nan=True):
        raise ContractError("forecast support/truth differ")
    if not np.isfinite(a[metric]).all() or not np.isfinite(b[metric]).all():
        raise ContractError("nonfinite common score")
    out = a.reset_index()[["game_id", "entity", "stat", "player", "date_et"]].copy()
    out["change"] = b[metric].to_numpy() - a[metric].to_numpy()
    return out


def bootstrap_change(frame, pooled=True):
    """Paired game bootstrap plus predeclared fixed seven-day calendar blocks."""
    grouped = frame.groupby("game_id", sort=True).change.agg(["sum", "count", "mean"])
    days = frame.groupby("game_id").date_et.first().reindex(grouped.index)
    if pooled:
        numer, denom = grouped["sum"].to_numpy(), grouped["count"].to_numpy()
    else:
        numer, denom = grouped["mean"].to_numpy(), np.ones(len(grouped))
    n = len(grouped)
    if not n:
        return {"games": 0, "change": None, "supported": False}
    rng = np.random.default_rng(20261125)
    w = rng.multinomial(n, np.full(n, 1 / n), size=10000)
    boot = (w @ numer) / (w @ denom)
    block = pd.to_datetime(days).map(lambda d: d.date().toordinal() // 7).to_numpy()
    _, codes = np.unique(block, return_inverse=True)
    nb = int(codes.max() + 1)
    bn, bd = np.bincount(codes, weights=numer), np.bincount(codes, weights=denom)
    bw = np.random.default_rng(20261125).multinomial(nb, np.full(nb, 1 / nb), size=10000)
    block_boot = (bw @ bn) / (bw @ bd)
    return {"games": n, "rows": len(frame), "supported_for_overall_ranking": n >= 100,
            "change": float(numer.sum() / denom.sum()), "ci95_game": np.quantile(boot, [.025, .975]).tolist(),
            "ci95_calendar_week": np.quantile(block_boot, [.025, .975]).tolist(), "calendar_blocks": nb}


def summarise(scores, joints):
    supported = scores[scores.supported]
    result = {"models": {}, "paired_changes": {}, "contexts": {}}
    fields = ["crps", "absolute_error", "bias", "covered50", "covered80", "covered95", "width50", "width80", "width95", "tail_low", "tail_high"]
    for model, part in supported.groupby("model"):
        result["models"][model] = {}
        for (entity, stat), group in part.groupby(["entity", "stat"]):
            key = entity + "/" + stat
            result["models"][model][key] = {"games": group.game_id.nunique(), "rows": len(group),
                 "pooled": {col: float(group[col].mean()) for col in fields},
                 "equal_game": {col: float(group.groupby("game_id")[col].mean().mean()) for col in fields},
                 "simulation_half_change": bootstrap_change(group.assign(change=group.crps_half2-group.crps_half1))}
        j = joints[joints.model.eq(model)]
        if len(j):
            result["models"][model]["joint"] = {col: float(j[col].mean()) for col in (
                "energy", "win_brier", "win_log_loss_smoothed", "ties_probability", "negative_score_probability", "covariance")}
            result["models"][model]["joint"]["raw_log_loss_infinite_games"] = int(j.win_log_loss_infinite.sum())
            result["models"][model]["joint"]["raw_log_loss_mean"] = None if j.win_log_loss_infinite.any() else float(j.win_log_loss.mean())
            result["models"][model]["joint"]["energy_shift_sensitivity"] = float((j.energy_second_shifts-j.energy).abs().mean())
            bins = pd.cut(j.p_home, [0,.2,.4,.6,.8,1], include_lowest=True)
            result["models"][model]["joint"]["win_reliability"] = {str(k): {"games": len(v), "probability": float(v.p_home.mean()), "won": float(v.home_won.mean())} for k, v in j.groupby(bins, observed=True)}
    ref = supported[supported.model.eq("incumbent")]
    for model in ("player_rate", "team_strength"):
        cand = supported[supported.model.eq(model)]
        result["paired_changes"][model] = {}
        for (entity, stat), group in cand.groupby(["entity", "stat"]):
            ref_group = ref[ref.entity.eq(entity) & ref.stat.eq(stat)]
            pair = paired_frame(ref_group, group)
            key = entity + "/" + stat
            result["paired_changes"][model][key] = {"pooled": bootstrap_change(pair), "equal_game": bootstrap_change(pair, False)}
        # Identical support is required within every named context, not just overall.
        result["contexts"][model] = {}
        for context in ("role", "minute_band", "month", "rest_group", "side"):
            contexts = {}
            for (entity, stat, label), group in cand.groupby(["entity", "stat", context], dropna=False):
                ref_group = ref[ref.entity.eq(entity) & ref.stat.eq(stat) & ref[context].eq(label)]
                pair = paired_frame(ref_group, group)
                if not len(pair):
                    continue
                # Context intervals use game resampling too; all are descriptive.
                report = bootstrap_change(pair)
                report["context_support"] = report["games"] >= 30 and (entity != "player" or len(group) >= 200)
                contexts[f"{entity}/{stat}/{label}"] = report
            result["contexts"][model][context] = contexts
    result["unsupported_rows"] = int((~scores.supported).sum())
    return result
