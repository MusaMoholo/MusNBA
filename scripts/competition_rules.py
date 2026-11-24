"""Frozen 2026-27 competition mechanics; no fitting or network access."""
from __future__ import annotations
from functools import lru_cache
from fractions import Fraction
import numpy as np

SCHEMA = 'nba-competitions-2026-v1'
GROUP_ABBRS = {
 'East A': ['BKN','DET','MIL','ORL','TOR'], 'East B': ['CLE','IND','MIA','NY','PHI'],
 'East C': ['ATL','BOS','CHA','CHI','WSH'], 'West A': ['DAL','DEN','HOU','PHX','UTAH'],
 'West B': ['LAC','MEM','MIN','NO','OKC'], 'West C': ['GS','LAL','POR','SAC','SA']}


def groups(teams, master):
    by_abbr = {t['abbr']: k for k,t in teams.items()}
    result = {name: [by_abbr[a] for a in abbrs] for name,abbrs in GROUP_ABBRS.items()}
    cup = [g for g in master if 'Group Play' in g.get('notes','')]
    assert len(cup) == 60 and len({g['game_id'] for g in cup}) == 60, 'Cup group calendar incomplete/duplicate'
    for name, tids in result.items():
        expected = {frozenset((a,b)) for a in tids for b in tids if a != b}
        found = [g for g in cup if g['home_id'] in tids and g['away_id'] in tids]
        assert len(found) == 10 and {frozenset((g['home_id'],g['away_id'])) for g in found} == expected
        for t in tids:
            assert sum(g['home_id']==t for g in found)==sum(g['away_id']==t for g in found)==2
            assert teams[t]['conf'] == name.split()[0]
    return result


def break_tie(tied, criteria, draw):
    """Split at the first discriminating criterion; restart on every remaining sub-tie."""
    if len(tied) < 2: return list(tied)
    for criterion in criteria(tied):
        values = {t: criterion(t) for t in tied}
        levels = sorted(set(values.values()), reverse=True)
        if len(levels) > 1:
            return [t for v in levels for t in break_tie([t for t in tied if values[t]==v],criteria,draw)]
    return sorted(tied,key=lambda t:draw[t],reverse=True)


def percentage(won, played):
    # Valid competition ties always have support; missing denominators compare neutrally, never invented wins.
    return Fraction(int(won),int(played)) if played else Fraction(0)


def cup_order(tids, wins, h2h_w, h2h_n, differential, points, previous, draw, head_to_head=True):
    def criteria(tied):
        c = []
        if head_to_head:
            c.append(lambda t: percentage(h2h_w[t,tied].sum(),h2h_n[t,tied].sum()))
        return c + [lambda t:differential[t],lambda t:points[t],lambda t:previous[t]]
    out=[]
    for w in sorted({int(wins[t]) for t in tids},reverse=True):
        out.extend(break_tie([t for t in tids if wins[t]==w],criteria,draw))
    return out


def standings(wins, h2h_w, h2h_n, differential, conf, division, draw):
    """Official recursive regular-season rules; returns conference ranks, division winners."""
    n=len(wins); div_winners=set()
    eligible={c:[i for i in range(n) if conf[i]==c and wins[i]>=sorted([wins[j] for j in range(n) if conf[j]==c],reverse=True)[9]] for c in set(conf)}
    def criteria(tied, division_only=False):
        same_div=len({division[t] for t in tied})==1
        def pct_vs(t,opp): return percentage(h2h_w[t,opp].sum(),h2h_n[t,opp].sum())
        head=lambda t:pct_vs(t,tied)
        div=lambda t:int(t in div_winners) if not division_only else 0
        c=[head,div] if len(tied)==2 else [div,head]
        if same_div: c.append(lambda t:pct_vs(t,[j for j in range(n) if division[j]==division[t]]))
        c += [lambda t:pct_vs(t,[j for j in range(n) if conf[j]==conf[t]]),lambda t:pct_vs(t,eligible[conf[t]])]
        if len(tied)==2: c.append(lambda t:pct_vs(t,eligible[next(c for c in eligible if c!=conf[t])]))
        c.append(lambda t:differential[t])
        return c
    for d in set(division):
        tids=[i for i in range(n) if division[i]==d]; best=max(wins[t] for t in tids)
        div_winners.add(break_tie([t for t in tids if wins[t]==best],lambda t:criteria(t,True),draw)[0])
    rank=np.zeros(n,np.uint8)
    for c in sorted(set(conf)):
        order=[]
        for w in sorted({int(wins[t]) for t in range(n) if conf[t]==c},reverse=True):
            order.extend(break_tie([t for t in range(n) if conf[t]==c and wins[t]==w],criteria,draw))
        rank[order]=np.arange(1,len(order)+1)
    return rank,div_winners


@lru_cache(maxsize=4096)
def _matching(tids, forbidden, costs):
    """Exact minimum-cost perfect matching, deterministic lexical tie resolution (10 vertices)."""
    n=len(tids); banned=set(forbidden); cost=np.asarray(costs).reshape(n,n)
    @lru_cache(None)
    def solve(mask):
        if not mask:return (0,())
        i=(mask & -mask).bit_length()-1; remaining=mask & ~(1<<i); best=None
        for j in range(i+1,n):
            if not (remaining>>j)&1 or tuple(sorted((tids[i],tids[j]))) in banned:continue
            tail=solve(remaining & ~(1<<j))
            if tail is None:continue
            candidate=(int(cost[i,j])+tail[0],((tids[i],tids[j]),)+tail[1])
            if best is None or candidate<best:best=candidate
        return best
    result=solve((1<<n)-1)
    if result is None:raise ValueError('No feasible filler matching')
    return result[1]


def fillers(orders, pair_counts, alternative=False):
    """Two cross-conference games,20 intra, degree2, one home/away; explicit draw assumption."""
    # orders: each conference's 11 nonqualifiers, best to worst.
    east,west=orders
    cross=[(east[-1],west[-1]),(east[-2],west[-2])]
    if alternative:cross=[(east[-1],west[-2]),(east[-2],west[-1])]
    rounds=[]; previous=[]
    for r in range(2):
        pairs=[cross[r]]
        for group in (east,west):
            tids=tuple(sorted(set(group)-set(cross[r])))
            costs=tuple(int(pair_counts[a,b]!=3)*10000+abs(group.index(a)-group.index(b))*10 for a in tids for b in tids)
            pairs.extend(_matching(tids,tuple(sorted(tuple(sorted(p)) for p in previous)),costs))
        rounds.append(pairs);previous.extend(pairs)
    # The degree-two graph is a union of cycles: orient cycles, guaranteeing one home/away per team.
    edges=[p for slate in rounds for p in slate]; adj={t:[] for t in east+west}
    for e,(a,b) in enumerate(edges):adj[a].append((b,e));adj[b].append((a,e))
    oriented={}; used=set()
    for start in sorted(adj):
        if all(e in used for _,e in adj[start]):continue
        cur=start
        while True:
            options=sorted((b,e) for b,e in adj[cur] if e not in used)
            if not options:break
            nxt,e=options[0];used.add(e);oriented[e]=(nxt,cur) if alternative else (cur,nxt);cur=nxt
    return [[oriented[r*11+j] for j in range(11)] for r in range(2)]
