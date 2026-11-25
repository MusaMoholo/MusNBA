"""Frozen C01 prior-rate and direct-team challengers; research only.

No incumbent fitting/loading helpers: every outcome read has an explicit source
predicate. Training ends before the development period, including residual fits.
"""
from __future__ import annotations

from datetime import date
import hashlib

import numpy as np
import pandas as pd

from analysis.c01_core import ContractError, require_prior
from analysis.c01_workbench import ROOT, BOX_MAP
from basketball_common import NBA_TEAM_IDS

CUTOFF = "2025-12-31"
# Dated membership evidence: analysis/b2_calendar_audit.py POLICIES, not labels
# inferred from scores. Cup championship games do not count as regular season.
CUP_FINALS = {"401607495", "401734908", "401809839"}
RATE_STATS = ("fg2m", "fg3m", "ftm", "oreb", "dreb", "ast")
XCOLS = ("home_off", "away_def", "away_off", "home_def", "pace", "home_rest", "away_rest", "home_missing", "away_missing")


def seed(kind, game_id, chunk=0):
    return int.from_bytes(hashlib.sha256(f"c01-{kind}-v1|{game_id}|{chunk}".encode()).digest()[:8], "little")


def assert_training(frame, cutoff=CUTOFF):
    if frame.empty or frame.date_et.isna().any() or frame.date_et.gt(cutoff).any():
        raise ContractError("future/unknown training outcome")


def training_sources():
    return [ROOT/"analysis/b2_calendar_audit.py"] + [
        p for year in range(2023, 2027) for p in (
            ROOT / f"data/derived/history/{year}/segments.parquet",
            ROOT / f"data/derived/history/{year}/on_court.parquet",
            ROOT / f"data/raw/hoopr/player_box_{year}.parquet")]


def load_training():
    segments, boxes, on_court = [], [], []
    for year in range(2023, 2027):
        # The parquet predicate is applied before deserialising outcome columns.
        s = pd.read_parquet(ROOT / f"data/derived/history/{year}/segments.parquet",
                            filters=[("date_et", "<=", CUTOFF), ("season_type", "==", 2)],
                            columns=["game_id", "date_et", "season_type", "game_ok", "offense", "defense", "off_home", "poss", "period"])
        s = s[s.game_ok & s.offense.isin(NBA_TEAM_IDS) & s.defense.isin(NBA_TEAM_IDS) & ~s.game_id.isin(CUP_FINALS)]
        ids = s.game_id.unique().tolist()
        b = pd.read_parquet(ROOT / f"data/raw/hoopr/player_box_{year}.parquet",
                           filters=[("game_id", "in", list(map(int, ids)))],
                           columns=["game_id", "athlete_id", "team_id", "team_score", "did_not_play", "assists"] + list(BOX_MAP.values()))
        b = b.dropna(subset=["athlete_id", "team_id"])
        b = b.assign(game_id=b.game_id.astype("int64").astype(str), player=b.athlete_id.astype("int64").astype(str), team=b.team_id.astype("int64").astype(str))
        o = pd.read_parquet(ROOT / f"data/derived/history/{year}/on_court.parquet",
                            filters=[("date_et", "<=", CUTOFF), ("season_type", "==", 2)],
                            columns=["game_id", "player", "team", "sec", "date_et"])
        segments.append(s)
        boxes.append(b)
        on_court.append(o[o.game_id.isin(ids)])
    seg = pd.concat(segments, ignore_index=True)
    box = pd.concat(boxes, ignore_index=True)
    on = pd.concat(on_court, ignore_index=True)
    dates = seg[["game_id", "date_et"]].drop_duplicates()
    box = box.merge(dates, on="game_id", validate="many_to_one")
    assert_training(box)
    assert_training(on)
    played = box[~box.did_not_play].merge(on[["game_id", "player", "team", "sec"]], on=["game_id", "player", "team"], how="left", validate="one_to_one")
    complete = played[[*BOX_MAP.values(), "assists", "sec"]].notna().all(axis=1) & played.sec.gt(0)
    players = played[complete].copy()
    players["minutes"] = players.sec / 60
    for target, source in [("fg3m", "three_point_field_goals_made"), ("ftm", "free_throws_made"),
                           ("oreb", "offensive_rebounds"), ("dreb", "defensive_rebounds"), ("ast", "assists")]:
        players[target] = players[source]
    players["fg2m"] = players.field_goals_made - players.fg3m
    if (players[list(RATE_STATS)] < 0).any().any():
        raise ContractError("negative training count")
    team_box = box.groupby(["game_id", "team"]).agg(points=("points", "sum"), official=("team_score", "first"), score_versions=("team_score", "nunique"))
    if (team_box.points != team_box.official).any() or team_box.score_versions.ne(1).any():
        raise ContractError("training official score identity")
    rows = []
    for gid, part in seg.groupby("game_id", sort=False):
        home = part.loc[part.off_home, "offense"].unique()
        away = part.loc[~part.off_home, "offense"].unique()
        if len(home) != 1 or len(away) != 1 or home[0] == away[0]:
            raise ContractError("training side identity")
        h, a = home[0], away[0]
        rows.append({"game_id": gid, "date_et": part.date_et.iloc[0], "home": h, "away": a,
                     "home_points": float(team_box.loc[(gid, h), "points"]), "away_points": float(team_box.loc[(gid, a), "points"]),
                     "home_poss": int(part.loc[part.offense.eq(h), "poss"].nunique()),
                     "away_poss": int(part.loc[part.offense.eq(a), "poss"].nunique())})
    games = pd.DataFrame(rows).sort_values(["date_et", "game_id"]).reset_index(drop=True)
    assert_training(games)
    return players, games, {"training_games": len(games), "player_games": len(players), "unsupported_player_rows": int((~complete).sum()),
                             "latest_training_date": games.date_et.max(), "cutoff": CUTOFF, "excluded_non_regular_cup_ids": sorted(CUP_FINALS)}


def player_fit(frame, cutoff=CUTOFF):
    assert_training(frame, cutoff)
    age = (pd.Timestamp(cutoff) - pd.to_datetime(frame.date_et)).dt.days.to_numpy()
    w = np.exp2(-age / 180)
    f = frame[["player", "minutes", *RATE_STATS]].copy()
    for col in ("minutes", *RATE_STATS):
        f[col] *= w
    grouped = f.groupby("player")[["minutes", *RATE_STATS]].sum()
    league = (grouped[list(RATE_STATS)].sum() / grouped.minutes.sum()).to_numpy(float)
    return {"cutoff": cutoff, "latest_input": str(frame.date_et.max()), "stats": list(RATE_STATS), "league": league.tolist(),
            "players": {pid: row.tolist() for pid, row in grouped.iterrows()}}


def draw_players(fit, game_id, ids, minutes, origin):
    if fit["cutoff"] >= origin:
        raise ContractError("future player rate/shrinkage origin")
    require_prior(origin, dict.fromkeys(("fit", "features", "normalisation", "missing_prior", "residuals", "calibration"), fit["latest_input"]))
    if minutes.shape != (1000, len(ids)) or not np.isfinite(minutes).all() or (minutes < 0).any():
        raise ContractError("invalid shared minutes")
    rng = np.random.default_rng(seed("player-rate", game_id))
    league = np.asarray(fit["league"])
    result = {stat: np.zeros(minutes.shape, dtype=np.int64) for stat in RATE_STATS}
    missing = []
    for i in sorted(range(len(ids)), key=lambda i: ids[i]):
        prior = fit["players"].get(ids[i])
        if prior is None:
            missing.append(ids[i])
            prior = [0.] * (len(RATE_STATS) + 1)
        exposure, *counts = prior
        for j, stat in enumerate(RATE_STATS):
            shape = counts[j] + 200 * league[j]
            rate = rng.gamma(shape, 1 / (exposure + 200), 1000) if shape > 0 else np.zeros(1000)
            result[stat][:, i] = rng.poisson(rate * minutes[:, i])
    result["pts"] = 2 * result["fg2m"] + 3 * result["fg3m"] + result["ftm"]
    result["reb"] = result["oreb"] + result["dreb"]
    result["min"] = minutes.copy()
    return result, missing


def team_features(games, evaluation=None):
    """All games on a day receive state from BEFORE that day, never each other."""
    assert_training(games)
    state, league, last = {}, np.zeros(4), {}
    # State entries: points scored, points allowed, offensive poss, defensive poss, games.
    state_day = None
    league = np.zeros(5)
    output = []
    for day, part in games.groupby("date_et", sort=True):
        day_date = date.fromisoformat(day)
        if state_day:
            decay = 2 ** (-(day_date - state_day).days / 180)
            league *= decay
            for value in state.values():
                value *= decay
        for r in part.to_dict("records"):
            if league[4] > 0:
                output.append({**r, **feature_row(r["home"], r["away"], day, state, league, last)})
        for r in part.to_dict("records"):
            for team, pts, opppts, poss, oppposs in [(r["home"], r["home_points"], r["away_points"], r["home_poss"], r["away_poss"]),
                                                   (r["away"], r["away_points"], r["home_points"], r["away_poss"], r["home_poss"])]:
                values = np.array([pts, opppts, poss, oppposs, 1.])
                state.setdefault(team, np.zeros(5))[:] += values
                league += values
                last[team] = day
        state_day = day_date
    final_state = {"teams": {k: v.tolist() for k, v in state.items()}, "league": league.tolist(), "last": last, "latest_input": games.date_et.max()}
    return pd.DataFrame(output), final_state


def feature_row(home, away, origin, state, league, last, schedule_rest=None):
    if league[4] <= 0:
        raise ContractError("no prior league support")
    lg = league / league[4]
    def side(team):
        v = np.asarray(state.get(team, np.zeros(5)))
        off = 100 * (v[0] + 20 * lg[0]) / (v[2] + 20 * lg[2])
        defense = 100 * (v[1] + 20 * lg[1]) / (v[3] + 20 * lg[3])
        pace = (v[2] + 20 * lg[2]) / (v[4] + 20)
        rest = min(7, (date.fromisoformat(origin) - date.fromisoformat(last[team])).days) if team in last else 7
        if schedule_rest is not None:
            rest = schedule_rest[team]
            if not np.isfinite(rest) or not 1 <= rest <= 7:
                raise ContractError("unsupported schedule rest")
        return off, defense, pace, rest, float(v[4] == 0)
    h, a = side(home), side(away)
    return dict(zip(XCOLS, (h[0], a[1], a[0], h[1], (h[2] + a[2]) / 2, h[3], a[3], h[4], a[4])))


def ridge_fit(frame, cutoff):
    assert_training(frame, cutoff)
    if len(frame) < 200:
        raise ContractError("insufficient ridge training games")
    x = frame[list(XCOLS)].to_numpy(float)
    y = frame[["home_points", "away_points"]].to_numpy(float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ContractError("unknown ridge input")
    mean, sd = x.mean(0), x.std(0)
    mean[-2:], sd[-2:] = 0, 1  # indicators are not continuous quantities
    sd[sd == 0] = 1
    design = np.column_stack([np.ones(len(x)), (x - mean) / sd])
    penalty = np.diag([0.] + [10.] * len(XCOLS))
    coef = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return {"mean": mean.tolist(), "sd": sd.tolist(), "coef": coef.tolist(), "latest_input": str(frame.date_et.max())}


def ridge_predict(fit, frame):
    x = frame[list(XCOLS)].to_numpy(float)
    if not np.isfinite(x).all():
        raise ContractError("unknown ridge forecast input")
    design = np.column_stack([np.ones(len(x)), (x - fit["mean"]) / fit["sd"]])
    return design @ np.asarray(fit["coef"])


def team_fit(features, state):
    residuals, residual_dates, residual_ids = [], [], []
    months = features.date_et.str[:7]
    for month in sorted(months.unique()):
        before = features[features.date_et.lt(month + "-01")]
        part = features[months.eq(month)]
        if len(before) < 200:
            continue
        fit = ridge_fit(before, cutoff=str(before.date_et.max()))
        if fit["latest_input"] >= part.date_et.min():
            raise ContractError("future residual fit")
        residuals.extend((part[["home_points", "away_points"]].to_numpy() - ridge_predict(fit, part)).tolist())
        residual_dates.extend(part.date_et.tolist())
        residual_ids.extend(part.game_id.tolist())
    if len(residuals) < 100:
        raise ContractError("insufficient chronological residual support")
    final = ridge_fit(features, CUTOFF)
    return {"fit": final, "state": state, "residuals": residuals[-500:], "residual_dates": residual_dates[-500:],
            "residual_ids": residual_ids[-500:], "latest_input": max(final["latest_input"], max(residual_dates))}


def draw_teams(fit, game_id, home, away, origin, rest):
    require_prior(origin, dict.fromkeys(("fit", "features", "normalisation", "missing_prior", "residuals", "calibration"), fit["latest_input"]))
    if max(fit["residual_dates"]) >= origin or fit["fit"]["latest_input"] >= origin or fit["state"]["latest_input"] >= origin:
        raise ContractError("future team auxiliary")
    state = fit["state"]
    row = feature_row(home, away, origin, state["teams"], np.asarray(state["league"]), state["last"], rest)
    mu = ridge_predict(fit["fit"], pd.DataFrame([row]))[0]
    errors = np.asarray(fit["residuals"])
    rng = np.random.default_rng(seed("team-strength", game_id))
    draws = mu + errors[rng.integers(len(errors), size=1000)] * rng.choice([-1., 1.], size=(1000, 1))
    return draws, row
