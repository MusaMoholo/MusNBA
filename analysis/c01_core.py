"""Small independent contracts for C01. No collectors, fitting or production imports.

Missing truth is unsupported, invalid forecasts are errors. Distribution scores use
the empirical law (including its atoms), not a clipped histogram approximation.
"""
from __future__ import annotations

from datetime import date, datetime
from numbers import Integral
import re

import numpy as np


class ContractError(ValueError):
    """A source, time or forecast boundary was violated."""


def source_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value):
        raise ContractError("source ID must be a digit string")
    return value


def unique_keys(rows, fields):
    keys = [tuple(row[k] for k in fields) for row in rows]
    if len(keys) != len(set(keys)):
        raise ContractError(f"duplicate key: {fields}")


def participation(dnp, minutes, counts=()):
    """Explicit absence and missing observation are different states."""
    known = minutes is not None and np.isfinite(minutes)
    values = np.asarray([x for x in counts if x is not None], dtype=float)
    if (known and minutes < 0) or (values < 0).any():
        raise ContractError("negative source box value")
    if dnp is True:
        if (known and minutes > 0) or (values[np.isfinite(values)] > 0).any():
            raise ContractError("DNP contradicts source minutes/counts")
        return "dnp"
    if dnp is False and known and minutes > 0:
        return "played"
    return "unknown"


def validate_box(rows, team_points):
    """Strict supported box fixture; unknown minutes remain outside this identity."""
    unique_keys(rows, ("game_id", "team", "player"))
    unique_keys(rows, ("game_id", "player"))
    if not rows or len(team_points) != 2:
        raise ContractError("box requires two teams and players")
    games = {source_id(r["game_id"]) for r in rows}
    if len(games) != 1:
        raise ContractError("box contains multiple games")
    totals = dict.fromkeys(team_points, 0)
    for row in rows:
        source_id(row["player"])
        source_id(row["team"])
        if row["team"] not in totals:
            raise ContractError("unknown box team")
        keys = ("pts", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "reb", "oreb", "dreb")
        a = np.asarray([row[k] for k in keys], dtype=float)
        # An explicit DNP proves zero counts even when the provider leaves the
        # box blank. Do not apply that interpretation to an unknown/played row,
        # and reject a contradictory nonzero count before filling absent fields.
        if row.get("dnp") is True:
            participation(True, row.get("minutes"), a)
            a = np.where(np.isnan(a), 0., a)
            row = {**row, **dict(zip(keys, a))}
        if not np.isfinite(a).all() or (a < 0).any() or (a != np.floor(a)).any():
            raise ContractError("box counts must be finite nonnegative integers")
        if row["pts"] != 2 * row["fgm"] + row["fg3m"] + row["ftm"]:
            raise ContractError("box scoring identity")
        if row["reb"] != row["oreb"] + row["dreb"]:
            raise ContractError("box rebound identity")
        if not (row["fg3m"] <= row["fgm"] <= row["fga"] and
                row["fg3m"] <= row["fg3a"] <= row["fga"] and row["ftm"] <= row["fta"] and
                row["fgm"] - row["fg3m"] <= row["fga"] - row["fg3a"]):
            raise ContractError("box makes/attempts identity")
        participation(row.get("dnp"), row.get("minutes"), a)
        totals[row["team"]] += row["pts"]
    if totals != team_points:
        raise ContractError("player/team points identity")
    return totals


def validate_minutes(rows, teams, final_period):
    """Reconstructed minutes, never rounded box minutes or rescaled truth."""
    unique_keys(rows, ("game_id", "player"))
    if not isinstance(final_period, Integral) or final_period < 4 or len(set(teams)) != 2:
        raise ContractError("invalid minute game/period")
    if not rows or len({source_id(r["game_id"]) for r in rows}) != 1:
        raise ContractError("minutes require one game")
    totals = dict.fromkeys(teams, 0.)
    cap = 48 + 5 * (final_period - 4)
    for row in rows:
        source_id(row["player"])
        if row["team"] not in totals:
            raise ContractError("unknown minute team")
        value = row["minutes"]
        if value is None or not np.isfinite(value):
            raise ContractError("unknown reconstructed minutes")
        if not 0 <= value <= cap:
            raise ContractError("illegal reconstructed minutes")
        totals[row["team"]] += value
    if any(abs(v - 5 * cap) > .05 for v in totals.values()):
        raise ContractError("team minutes identity")
    return totals


def validate_events(rows, teams, final_period, official_points, other_points):
    """Validate ordered segment fixtures; separately evidenced other points required.

    This is a measurement boundary, not the incumbent segment parser. A source
    adapter may expose an unsupported result instead of certifying bad rows.
    """
    if not isinstance(final_period, Integral) or final_period < 4:
        raise ContractError("invalid final period")
    if len(set(teams)) != 2 or set(official_points) != set(teams) or set(other_points) != set(teams):
        raise ContractError("event teams differ")
    unique_keys(rows, ("game_id", "event_index"))
    if not rows or len({source_id(r["game_id"]) for r in rows}) != 1:
        raise ContractError("events require one game")
    points, possessions = dict.fromkeys(teams, 0), {t: set() for t in teams}
    last_period, next_clock, seen, owners = 0, None, set(), {}
    for row in rows:
        p = row["period"]
        if not isinstance(p, Integral) or not 1 <= p <= final_period or p < last_period:
            raise ContractError("invalid/unordered event period")
        length = 720 if p <= 4 else 300
        if p != last_period:
            if last_period and abs(next_clock) > .11:
                raise ContractError("period did not end at zero")
            next_clock = length
        clocks = np.asarray([row[k] for k in ("start_clock", "action_clock", "end_clock")], dtype=float)
        if not np.isfinite(clocks).all() or not (length >= clocks[0] >= clocks[1] >= clocks[2] >= 0):
            raise ContractError("broken event clocks")
        if abs(clocks[0] - next_clock) > .11:
            raise ContractError("event clock gap/overlap")
        off, defense = row["offense"], row["defense"]
        if {off, defense} != set(teams):
            raise ContractError("invalid event team IDs")
        fives = [row["lineup_off"], row["lineup_def"]]
        if any(len(f) != 5 or len(set(f)) != 5 for f in fives) or set(fives[0]) & set(fives[1]):
            raise ContractError("invalid on-court fives")
        for pid in fives[0] + fives[1]:
            source_id(pid)
        if row.get("actor") is not None and row["actor"] not in fives[0]:
            raise ContractError("actor outside offensive five")
        if not isinstance(row["poss"], Integral) or row["poss"] < 0:
            raise ContractError("invalid possession ID")
        if row["poss"] in owners and owners[row["poss"]] != off:
            raise ContractError("possession ID belongs to both teams")
        owners[row["poss"]] = off
        if not isinstance(row["points"], Integral) or row["points"] < 0:
            raise ContractError("invalid event points")
        possessions[off].add(row["poss"])
        points[off] += row["points"]
        next_clock, last_period = clocks[2], p
        seen.add(p)
    if seen != set(range(1, final_period + 1)) or abs(next_clock) > .11:
        raise ContractError("incomplete event periods")
    if any(not isinstance(other_points[t], Integral) or other_points[t] < 0 or
           points[t] + other_points[t] != official_points[t] for t in teams):
        raise ContractError("segment plus other points identity")
    return {"points": points, "possessions": {t: len(v) for t, v in possessions.items()},
            "team_minutes": 240 + 25 * (final_period - 4)}


def require_prior(origin, provenance):
    """All auxiliaries have explicit latest input dates; same-day outcomes fail.

    Date-level historical origin deliberately excludes the entire evaluated ET
    day. Timestamp-level pre-tip capture is a separate, stricter population.
    """
    boundary = date.fromisoformat(origin)
    required = {"fit", "features", "normalisation", "missing_prior", "residuals", "calibration"}
    if set(provenance) != required:
        raise ContractError("missing/extra cutoff provenance fields")
    for field, latest in provenance.items():
        if latest is None or date.fromisoformat(latest) >= boundary:
            raise ContractError(f"future/unknown {field} input")
    return True


def require_pre_tip(tip, times):
    """Do not infer historical publication time from the event's date."""
    def stamp(value):
        if not isinstance(value, str):
            raise ContractError("unknown pre-tip timestamp")
        try:
            out = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ContractError("invalid pre-tip timestamp") from exc
        if out.tzinfo is None:
            raise ContractError("pre-tip timestamps require timezone")
        return out
    boundary = stamp(tip)
    fields = {"captured", "model_fitted", "input_as_of", "report_published", "report_retrieved"}
    if set(times) != fields:
        raise ContractError("missing/extra pre-tip provenance fields")
    parsed = {k: stamp(v) for k, v in times.items()}
    if any(t >= boundary for t in parsed.values()):
        raise ContractError("late pre-tip input/capture")
    if not (parsed["report_published"] <= parsed["report_retrieved"] <= parsed["captured"] and
            parsed["model_fitted"] <= parsed["captured"] and parsed["input_as_of"] <= parsed["captured"]):
        raise ContractError("inconsistent pre-tip provenance order")
    return True


def distribution(samples, weights=None):
    x = np.asarray(samples, dtype=float)
    if x.ndim != 1 or not x.size or not np.isfinite(x).all():
        raise ContractError("forecast samples must be finite nonempty vector")
    w = np.full(x.size, 1 / x.size) if weights is None else np.asarray(weights, dtype=float)
    if w.shape != x.shape or not np.isfinite(w).all() or (w < 0).any() or abs(w.sum() - 1) > 1e-12:
        raise ContractError("forecast weights must be finite, nonnegative and sum to one")
    order = np.argsort(x, kind="stable")
    return x[order], w[order]


def score(samples, truth, weights=None):
    x, w = distribution(samples, weights)
    if truth is None or not np.isfinite(truth):
        return {"supported": False, "reason": "missing truth"}
    # The integrated empirical CDF formula differs from the pairwise reference.
    c = np.cumsum(w)[:-1]
    spread = np.sum(c * (1 - c) * np.diff(x))
    crps = np.sum(w * np.abs(x - truth)) - spread
    mean = np.sum(x * w)
    bounds = [float(w[x < truth].sum()), float(w[x <= truth].sum())]
    intervals = {}
    cdf = np.cumsum(w)
    def quantile(p):
        return float(x[min(np.searchsorted(cdf, p, side="left"), len(x) - 1)])
    for level in (.5, .8, .95):
        lo, hi = quantile((1 - level) / 2), quantile((1 + level) / 2)
        intervals[str(level)] = {"lo": lo, "hi": hi, "width": hi - lo, "covered": lo <= truth <= hi}
    return {"supported": True, "crps": float(crps), "mean": float(mean),
            "bias": float(mean - truth), "absolute_error": float(abs(mean - truth)),
            "rank_bounds": bounds, "intervals": intervals}


def reference_crps(samples, truth, weights=None):
    """Independent O(n²) definition for small arithmetic fixtures only."""
    values = list(map(float, samples))
    mass = [1 / len(values)] * len(values) if weights is None else list(map(float, weights))
    first = sum(p * abs(v - truth) for p, v in zip(mass, values))
    second = sum(p * q * abs(v - u) for v, p in zip(values, mass) for u, q in zip(values, mass))
    return first - second / 2


def probability_score(probabilities, observed):
    p = np.asarray(probabilities, dtype=float)
    if p.ndim != 1 or not p.size or not np.isfinite(p).all() or (p < 0).any() or abs(p.sum() - 1) > 1e-12:
        raise ContractError("invalid class probabilities")
    if not isinstance(observed, Integral) or not 0 <= observed < len(p):
        raise ContractError("invalid observed class")
    actual = np.arange(len(p)) == observed
    return {"log_loss": float(-np.log(p[observed])) if p[observed] else float("inf"),
            "brier": float(np.sum((p - actual) ** 2))}
