"""Canonical, world-local 2026-27 paths on unchanged pathway-v1 rating mechanics.

Production computation only; views read its persisted receipts. Each 1k chunk has its own
seed/namespace, independent of process assignment. No provider access or fitting here.
"""
from __future__ import annotations
import base64
import hashlib
import json
import math
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from scripts import pathway, competition_rules as rules
from scripts.projection import seed_for

ROOT=Path(__file__).resolve().parent.parent
POLICY=ROOT/'models/competitions_2026.json'
STAGES={'regular':0,'group':1,'cup_qf':2,'cup_sf':3,'filler':4,'cup_final':5,'playin':6,'round1':7,'round2':8,'conference':9,'finals':10}


def prepare(master, teams, day):
    if not all(g['season']=='2026-27' for g in master):raise ValueError('Competition version requires 2026-27')
    group=rules.groups(teams,master)
    ids=sorted(teams,key=int); index={t:i for i,t in enumerate(ids)}
    actual=[];base=[]
    for g in master:
        if '2026-12-04'<=g['date_et']<='2026-12-11':actual.append(g)
        else:base.append(g)
    counts=np.zeros(30,int);pairs=np.zeros((30,30),int)
    for g in base:
        h,a=index[g['home_id']],index[g['away_id']];counts[[h,a]]+=1;pairs[h,a]+=1;pairs[a,h]+=1
    if not np.all(counts==80):raise ValueError('Unrecognised base calendar: expected80/team; no invented completion')
    if len({g['game_id'] for g in master})!=len(master):raise ValueError('Duplicate provider event ID')
    past={}
    # Past regulation totals are required for Cup; missing period truth is an error, not a score estimate.
    from basketball_common import RAW,read_json
    for g in master:
        if g['date_et']>=day:continue
        if g['status']!='final':raise ValueError('Unresolved game before origin: '+g['game_id'])
        full=(int(g['home_pts']),int(g['away_pts']))
        p=RAW/'final'/f"{g['game_id']}.json.gz"
        sides={x['homeAway']:x for x in read_json(p)['header']['competitions'][0]['competitors']}
        reg=[]
        for side in ('home','away'):
            ls=sides[side].get('linescores',[])
            if len(ls)<4:raise ValueError('Missing recorded regulation scores')
            reg.append(sum(int(float(x.get('displayValue',x.get('value')))) for x in ls[:4]))
        if (reg[0]!=reg[1]) != (int(g['periods'])==4):raise ValueError('Recorded period/OT inconsistency')
        past[g['game_id']]={'reg':reg,'final':full,'ot':int(g['periods'])-4,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    return {'ids':ids,'group':{k:[index[t] for t in v] for k,v in group.items()},'base':base,'actual':actual,
            'pairs':pairs,'past':past,'policy':json.loads(POLICY.read_text()),'day':day,'teams':teams}


class Paths:
    def __init__(self,T,lg,prepared,W,rng,aux,engine=None,params=None):
        self.W=W;self.prep=prepared;self.ids=prepared['ids'];self.index={t:i for i,t in enumerate(self.ids)}
        self.rng=rng;self.aux=aux;self.engine=engine or {};self.lg=lg;self.p={**pathway.PATHWAY,**(params or {})}
        off,dfn,self.pace,gp=pathway.start_ratings(T,lg,self.ids,self.p['K'])
        sd=self.p['sigma']/np.sqrt(gp+self.p['K'])
        self.off=off+ self.p['start_scale']*sd*rng.standard_normal((W,30))
        self.dfn=dfn+ self.p['start_scale']*sd*rng.standard_normal((W,30))
        self.n=np.broadcast_to(gp,(W,30)).copy();self.start={'off':off,'def':dfn,'pace':self.pace,'sd':sd}
        self.rows=np.arange(W);self.events=[];self.event_ids=set();self.past_applied=set()
        self.h2w=np.zeros((W,30,30),np.uint8);self.h2n=self.h2w.copy();self.wins=np.zeros((W,30),np.uint8)
        self.diff=np.zeros((W,30),np.int32);self.gp=np.zeros((W,30),np.uint8)
        self.cw=np.zeros((W,30),np.uint8);self.cd=self.diff.copy();self.cp=self.diff.copy()
        self.chw=self.h2w.copy();self.chn=self.h2n.copy();self.used_actual=set()
        self.base_w=np.array([T[t]['w'] for t in self.ids]);self.base_l=np.array([T[t]['l'] for t in self.ids])
        self.scheduled={};self.last_key='';self.negative_rejections=0

    def _ot(self,mu_h,mu_a,reg,win):
        final=reg.copy();tie=reg[:,0]==reg[:,1];periods=np.zeros(self.W,np.uint8)
        pending=np.flatnonzero(tie)
        # Conditional rejection preserves the accepted Bernoulli OT winner and samples a full compatible score.
        while len(pending):
            k=pending; share=self.p['ot_share'];sd=self.p['team_sd']*math.sqrt(share);rho=self.p['team_rho']
            z=self.aux.standard_normal((len(k),2));x=np.rint(mu_h[k]*share+sd*z[:,0]).astype(np.int32)
            y=np.rint(mu_a[k]*share+sd*(rho*z[:,0]+math.sqrt(1-rho*rho)*z[:,1])).astype(np.int32)
            valid=(x>=0)&(y>=0);self.negative_rejections+=int((~valid).sum())
            # Tied periods can repeat; terminal periods must match the preselected winner.
            accept=valid&((x==y)|((x>y)==win[k]));q=k[accept]
            final[q,0]+=x[accept];final[q,1]+=y[accept];periods[q]+=1
            pending=np.r_[k[~accept],q[x[accept]==y[accept]]]
            if periods.max(initial=0)>100:raise ValueError('Implausible OT sampling failed; no clipping')
        return final,periods

    def assigned_fixture(self,stage,h,a):
        """Known slots constrain their own participants; other slots remain world-local."""
        matches=[]
        for g in self.prep['actual']:
            notes=g.get('notes','').lower()
            kind='cup_final' if 'championship' in notes else 'cup_qf' if 'quarterfinal' in notes or 'quarter-final' in notes else 'cup_sf' if 'semifinal' in notes or 'semi-final' in notes else 'filler'
            if kind==stage:matches.append(g)
        if not matches:return None
        possible=[g for g in matches if np.all(((h==self.index[g['home_id']])&(a==self.index[g['away_id']]))|((a==self.index[g['home_id']])&(h==self.index[g['away_id']])))]
        if len(possible)==1:return possible[0]
        if len(possible)>1:raise ValueError('Duplicate assigned slot')
        known={self.index[g[side+'_id']] for g in matches for side in ('home','away')}
        if np.isin(h,list(known)).any() or np.isin(a,list(known)).any():
            raise ValueError('Assigned fixture contradicts world-local slot')
        return None

    def slot_date(self,stage,h,a,default):
        g=self.assigned_fixture(stage,np.asarray(h),np.asarray(a))
        return g['date_et'] if g else default

    def event(self,eid,date,stage,h,a,neutral=False,active=None,provider=None):
        h=np.broadcast_to(np.asarray(h,int),(self.W,));a=np.broadcast_to(np.asarray(a,int),(self.W,))
        if np.any(h==a):raise ValueError('Self match')
        mask=np.ones(self.W,bool) if active is None else np.asarray(active,bool);r=self.rows
        regular=STAGES[stage]<=4;cup=stage in ('group','cup_qf','cup_sf','cup_final')
        # Replace a known slot once; absence of other stage assignments is not an error.
        assigned=self.assigned_fixture(stage,h,a) if provider is None else None
        if assigned is not None:
            provider=assigned;eid=provider['game_id'];h=np.full(self.W,self.index[provider['home_id']]);a=np.full(self.W,self.index[provider['away_id']]);date=provider['date_et']
            neutral=bool(int(provider.get('neutral') or 0));self.used_actual.add(eid)
        if eid in self.event_ids:raise ValueError('Duplicate canonical event')
        if date<self.last_key:raise ValueError('Nonchronological event')
        self.last_key=date;self.event_ids.add(eid)
        if date<self.prep['day']:
            truth=self.prep['past'].get(eid)
            if truth is None:raise ValueError('Missing canonical past outcome '+eid)
            reg=np.broadcast_to(truth['reg'],(self.W,2)).copy();final=np.broadcast_to(truth['final'],(self.W,2)).copy();ot=np.full(self.W,truth['ot'],np.uint8)
            win=final[:,0]>final[:,1];update=False;self.past_applied.add(eid)
        else:
            pace=self.pace[h]*self.pace[a]/self.lg['pace'];hca=0 if neutral else self.p['home_court']
            mh=pace*self.off[r,h]*self.dfn[r,a]/self.lg['ortg']/100+hca/2
            ma=pace*self.off[r,a]*self.dfn[r,h]/self.lg['ortg']/100-hca/2
            e=self.engine.get(eid)
            if e is not None:
                reg=e[:,:,:4].sum(2).astype(np.int32);final=e.sum(2).astype(np.int32);win=final[:,0]>final[:,1]
                # Combined engine OT has an exact total, but no recoverable period count:255 means unknown.
                ot=np.where(reg[:,0]==reg[:,1],255,0).astype(np.uint8)
            else:
                sd=self.p['team_sd'];rho=self.p['team_rho'];z1=self.rng.standard_normal(self.W)
                z2=rho*z1+math.sqrt(1-rho*rho)*self.rng.standard_normal(self.W)
                reg=np.stack((np.rint(mh+sd*z1),np.rint(ma+sd*z2)),1).astype(np.int32)
                if np.any(reg<0):raise ValueError('Negative simulated regulation score; no clamping')
                p_ot=.5*(1+pathway._erf((mh-ma)*self.p['ot_share']/(sd*math.sqrt(2*(1-rho)*self.p['ot_share']))/math.sqrt(2)))
                win=np.where(reg[:,0]==reg[:,1],self.rng.random(self.W)<p_ot,reg[:,0]>reg[:,1])
                final,ot=self._ot(mh,ma,reg,win)
            sh=100*(reg[:,0]-mh)/pace;sa=100*(reg[:,1]-ma)/pace;k=self.p['K'];cap=self.p.get('n_cap') or np.inf
            gh=self.p['scale']/(np.minimum(self.n[r,h],cap)+1+k);ga=self.p['scale']/(np.minimum(self.n[r,a],cap)+1+k)
            q=r[mask];hh=h[mask];aa=a[mask]
            self.off[q,hh]+=gh[mask]*sh[mask];self.dfn[q,aa]+=ga[mask]*sh[mask]
            self.off[q,aa]+=ga[mask]*sa[mask];self.dfn[q,hh]+=gh[mask]*sa[mask]
            self.n[q,hh]+=1;self.n[q,aa]+=1;update=True
        if np.any((final[:,0]==final[:,1])&mask):raise ValueError('Tied final')
        q=r[mask];hh=h[mask];aa=a[mask];ww=win[mask]
        if regular:
            self.gp[q,hh]+=1;self.gp[q,aa]+=1;self.wins[q,np.where(ww,hh,aa)]+=1
            self.h2n[q,hh,aa]+=1;self.h2n[q,aa,hh]+=1;self.h2w[q,np.where(ww,hh,aa),np.where(ww,aa,hh)]+=1
            delta=(final[:,0]-final[:,1])[mask];self.diff[q,hh]+=delta;self.diff[q,aa]-=delta
        if stage=='group':
            self.cw[q,np.where(ww,hh,aa)]+=1;delta=(reg[:,0]-reg[:,1])[mask]
            self.cd[q,hh]+=delta;self.cd[q,aa]-=delta;self.cp[q,hh]+=reg[mask,0];self.cp[q,aa]+=reg[mask,1]
            self.chn[q,hh,aa]+=1;self.chn[q,aa,hh]+=1;self.chw[q,np.where(ww,hh,aa),np.where(ww,aa,hh)]+=1
        rec={'id':eid,'date':date,'stage':stage,'regular':regular,'cup':cup,'neutral':bool(neutral),'home':h.astype(np.uint8),'away':a.astype(np.uint8),
             'reg':reg,'final':final,'ot':ot,'active':mask,'winner':np.where(win,h,a).astype(np.uint8),'updated':update}
        self.events.append(rec)
        if provider is not None and eid not in self.used_actual:self.scheduled[eid]=(win,reg)
        return rec['winner'],np.where(win,a,h).astype(np.uint8)

    def regular(self):
        before=[g for g in self.prep['base'] if g['date_et']<'2026-12-04']
        after=[g for g in self.prep['base'] if g['date_et']>'2026-12-11']
        for g in before:self.event(g['game_id'],g['date_et'],'group' if 'Group Play' in g.get('notes','') else 'regular',self.index[g['home_id']],self.index[g['away_id']],bool(int(g.get('neutral') or 0)),provider=g)
        self.cup()
        for g in after:self.event(g['game_id'],g['date_et'],'regular',self.index[g['home_id']],self.index[g['away_id']],bool(int(g.get('neutral') or 0)),provider=g)
        if not np.all(self.gp==82):raise ValueError('Calendar did not produce82/team')
        if set(self.prep['past'])!=self.past_applied:raise ValueError('Past events omitted or duplicated')

    def cup(self):
        W=self.W;previous=np.array([self.prep['policy']['prior_regular_wins'][t] for t in self.ids]);draw=self.aux.random((W,30))
        qualifiers=np.zeros((W,8),np.uint8);non=[np.zeros((W,11),np.uint8),np.zeros((W,11),np.uint8)]
        self.cup_rank=np.zeros((W,30),np.uint8);self.cup_group=np.zeros((W,30),np.uint8)
        for w in range(W):
            for ci,conf in enumerate(('East','West')):
                ranked=[]
                for name,tids in self.prep['group'].items():
                    if not name.startswith(conf):continue
                    order=rules.cup_order(tids,self.cw[w],self.chw[w],self.chn[w],self.cd[w],self.cp[w],previous,draw[w])
                    self.cup_group[w,order]=np.arange(1,6);ranked.append(order)
                winners=rules.cup_order([v[0] for v in ranked],self.cw[w],self.chw[w],self.chn[w],self.cd[w],self.cp[w],previous,draw[w],False)
                wildcard=rules.cup_order([v[1] for v in ranked],self.cw[w],self.chw[w],self.chn[w],self.cd[w],self.cp[w],previous,draw[w],False)[0]
                q=winners+[wildcard];qualifiers[w,ci*4:ci*4+4]=q
                rest=rules.cup_order([t for v in ranked for t in v if t not in q],self.cw[w],self.chw[w],self.chn[w],self.cd[w],self.cp[w],previous,draw[w],False)
                non[ci][w]=rest;self.cup_rank[w,q+rest]=np.arange(1,16)
        filler=np.zeros((W,2,11,2),np.uint8)
        assigned=[g for g in self.prep['actual'] if 'cup' not in g.get('notes','').lower()]
        nonqualifier_games=[]
        for g in assigned:
            h,a=self.index[g['home_id']],self.index[g['away_id']]
            if np.all(~np.isin(qualifiers,[h,a]).any(axis=1)):nonqualifier_games.append(g)
        if len(nonqualifier_games) not in (0,22):
            raise ValueError('Incomplete nonqualifier provider draw; no unsafe matching completion')
        if not nonqualifier_games:
            for w in range(W):filler[w]=rules.fillers([list(x[w]) for x in non],self.prep['pairs'],self.prep.get('alternative',False))
        # Actual dates can interleave conferences. Keep bracket slots separate from execution order.
        qf=[None]*4;losers=[None]*4;loser_home=[None]*4;requests=[]
        for ci in range(2):
            for j,(u,v) in enumerate(((0,3),(1,2))):
                h,a=qualifiers[:,4*ci+u],qualifiers[:,4*ci+v]
                date=self.slot_date('cup_qf',h,a,f'2026-12-0{4+ci}')
                requests.append((date,ci,j,h,a))
        for date,ci,j,h,a in sorted(requests,key=lambda r:r[:3]):
            k=2*ci+j
            qf[k],losers[k]=self.event(f'c5:2026:cup:qf:{ci}:{j}',date,'cup_qf',h,a)
            loser_home[k]=losers[k]==self.events[-1]['home']
        loser_games=[];semifinals=[]
        for ci in range(2):
            a,b=losers[2*ci:2*ci+2];loser_games.append(self.assigned_fixture('filler',a,b))
            a,b=qf[2*ci:2*ci+2];higher=self.cup_rank[self.rows,a]<self.cup_rank[self.rows,b]
            h,a2=np.where(higher,a,b),np.where(higher,b,a)
            date=self.slot_date('cup_sf',h,a2,f'2026-12-0{8+ci}')
            semifinals.append((date,h,a2))
        fillers_by_date=({d:[g for g in nonqualifier_games if g['date_et']==d] for d in {g['date_et'] for g in nonqualifier_games}}
                         if nonqualifier_games else {'2026-12-06':list(range(11)),'2026-12-10':list(range(11))})
        finalists=[None,None]
        for d in ('2026-12-06','2026-12-07','2026-12-08','2026-12-09','2026-12-10'):
            for j,g in enumerate(fillers_by_date.get(d,[])):
                if nonqualifier_games:
                    self.event(g['game_id'],d,'filler',self.index[g['home_id']],self.index[g['away_id']],provider=g);self.used_actual.add(g['game_id'])
                else:
                    rr=0 if d=='2026-12-06' else 1
                    self.event(f'c5:2026:filler:{rr}:{j}',d,'filler',filler[:,rr,j,0],filler[:,rr,j,1])
            for ci in range(2):
                g=loser_games[ci]
                if g is not None:
                    if g['date_et']!=d:continue
                    self.event(g['game_id'],d,'filler',self.index[g['home_id']],self.index[g['away_id']],provider=g);self.used_actual.add(g['game_id'])
                elif d=='2026-12-07':
                    a,b=losers[2*ci:2*ci+2];ah,bh=loser_home[2*ci:2*ci+2];a_hosts=ah<=bh
                    self.event(f'c5:2026:qf-loser:{ci}',d,'filler',np.where(a_hosts,a,b),np.where(a_hosts,b,a))
            for ci,(date,h,a) in enumerate(semifinals):
                if date==d:finalists[ci],_=self.event(f'c5:2026:cup:sf:{ci}',d,'cup_sf',h,a)
        self.cup_champion,_=self.event('c5:2026:cup:final','2026-12-11','cup_final',finalists[0],finalists[1],True)
        self.cup_qualifiers=qualifiers
        if self.prep['actual'] and {g['game_id'] for g in self.prep['actual']}!=self.used_actual:raise ValueError('Unused assigned fixture')

    def postseason(self):
        conf=[self.prep['teams'][t]['conf'] for t in self.ids];division=[self.prep['teams'][t]['div'] for t in self.ids]
        self.seed=np.zeros((self.W,30),np.uint8);draw=self.aux.random((self.W,30));self.div_winners=np.zeros((self.W,30),bool)
        for w in range(self.W):
            self.seed[w],d=rules.standings(self.wins[w],self.h2w[w],self.h2n[w],self.diff[w],conf,division,draw[w]);self.div_winners[w,list(d)]=True
        brackets=[];self.playoff_seed=np.zeros((self.W,30),np.uint8);self.reach=np.zeros((self.W,30),np.uint8)
        # Both conferences' first play-in games occur before either final play-in game.
        pin=[]
        for ci,c in enumerate(('East','West')):
            order=np.stack([np.argwhere((self.seed==s)&(np.array(conf)==c))[:,1] for s in range(1,11)],1)
            p7,l78=self.event(f'c5:2027:playin:{ci}:78','2027-04-13','playin',order[:,6],order[:,7])
            p9,_=self.event(f'c5:2027:playin:{ci}:910','2027-04-13','playin',order[:,8],order[:,9]);pin.append((order,p7,l78,p9))
        for ci,(order,p7,l78,p9) in enumerate(pin):
            p8,_=self.event(f'c5:2027:playin:{ci}:8','2027-04-16','playin',l78,p9)
            seeds=np.column_stack((order[:,:6],p7,p8));self.playoff_seed[self.rows[:,None],seeds]=np.arange(1,9)
            self.reach[self.rows[:,None],seeds]=1
            brackets.extend([(seeds[:,a],seeds[:,b]) for a,b in ((0,7),(3,4),(1,6),(2,5))])
        self.series=[]
        # Fixed bracket:1/8 vs4/5 and2/7 vs3/6. Global round barriers avoid advancing ratings out of order.
        from datetime import date,timedelta
        start=date(2027,4,17)
        for rnd,stage in enumerate(('round1','round2','conference','finals')):
            participants=[]
            for sid,(a,b) in enumerate(brackets):
                if rnd<3:higher=self.seed[self.rows,a]<self.seed[self.rows,b]
                else:
                    # Finals: better regular record; then H2H; conference record; final seeded drawing.
                    aw=self.wins[self.rows,a];bw=self.wins[self.rows,b]
                    hh=self.h2w[self.rows,a,b]-self.h2w[self.rows,b,a].astype(int)
                    own=np.array(conf)
                    crA=np.array([rules.percentage(self.h2w[w,a[w],own!=own[a[w]]].sum(),self.h2n[w,a[w],own!=own[a[w]]].sum()) for w in range(self.W)],object)
                    crB=np.array([rules.percentage(self.h2w[w,b[w],own!=own[b[w]]].sum(),self.h2n[w,b[w],own!=own[b[w]]].sum()) for w in range(self.W)],object)
                    higher=np.where(aw!=bw,aw>bw,np.where(hh!=0,hh>0,np.where(crA!=crB,crA>crB,draw[self.rows,a]>draw[self.rows,b])))
                participants.append((np.where(higher,a,b),np.where(higher,b,a)))
            wins=np.zeros((self.W,len(brackets),2),np.uint8);length=np.zeros((self.W,len(brackets)),np.uint8)
            for game in range(7):
                for sid,(a,b) in enumerate(participants):
                    active=wins[:,sid].max(1)<4;home_a=game in (0,1,4,6)
                    h,a2=(a,b) if home_a else (b,a)
                    winner,_=self.event(f'c5:2027:{stage}:{sid}:g{game+1}',str(start+timedelta(days=2*game)),stage,h,a2,active=active)
                    wins[:,sid,0]+=active&(winner==a);wins[:,sid,1]+=active&(winner==b);length[:,sid]+=active
            advanced=[]
            for sid,(a,b) in enumerate(participants):
                winner=np.where(wins[:,sid,0]==4,a,b).astype(np.uint8);advanced.append(winner)
                self.reach[self.rows,winner]=rnd+2
                self.series.append({'stage':stage,'slot':sid,'a':a,'b':b,'winner':winner,'length':length[:,sid]})
            brackets=[(advanced[i],advanced[i+1]) for i in range(0,len(advanced)-1,2)]
            start+=timedelta(days=16)
        self.champion=advanced[0]


def run_chunk(args):
    T,lg,prep,engine,W,seed,params=args
    import pyarrow as pa
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    x=Paths(T,lg,prep,W,np.random.default_rng(seed),np.random.default_rng(seed_for(seed,'auxiliary-OT-draw')),engine,params)
    x.regular();x.postseason()
    return x


def audit(x):
    """Independent accounting from canonical event ledger, without internal standings counters."""
    W=x.W;r=np.arange(W);gp=np.zeros((W,30),int);wins=gp.copy();diff=gp.copy();stage_counts={}
    prior_date='';seen=set();cup_count=np.zeros(W,int);pin=np.zeros(W,int)
    for e in x.events:
        if e['id'] in seen or e['date']<prior_date:raise AssertionError('Event identity/order')
        seen.add(e['id']);prior_date=e['date'];m=e['active'];q=r[m];h=e['home'][m].astype(int);a=e['away'][m].astype(int)
        reg=e['reg'][m];full=e['final'][m];winner=e['winner'][m]
        assert np.all(h!=a) and np.all(full>=reg) and np.all(full[:,0]!=full[:,1])
        assert np.array_equal(winner,np.where(full[:,0]>full[:,1],h,a))
        assert np.all((reg[:,0]==reg[:,1])==(e['ot'][m]>0))
        assert np.all((full==reg).all(1)==(e['ot'][m]==0))
        stage_counts[e['stage']]=stage_counts.get(e['stage'],np.zeros(W,int))+m
        if e['regular']:
            gp[q,h]+=1;gp[q,a]+=1;wins[q,winner]+=1;d=full[:,0]-full[:,1];diff[q,h]+=d;diff[q,a]-=d
        if e['cup']:cup_count+=m
        if e['stage']=='playin':pin+=m
        if e['stage']=='cup_final':assert e['neutral'] and not e['regular']
        if e['stage'] in ('cup_qf','cup_sf'):
            assert e['regular'] and np.all(x.cup_rank[q,h]<x.cup_rank[q,a])
    assert np.all(gp==82) and np.all(wins.sum(1)==1230)
    assert np.array_equal(wins,x.wins) and np.array_equal(diff,x.diff)
    assert np.all(cup_count==67) and np.all(pin==6)
    assert np.all((x.playoff_seed>0).sum(1)==16)
    assert np.all((x.reach>=2).sum(1)==8) and np.all((x.reach>=3).sum(1)==4) and np.all((x.reach>=4).sum(1)==2) and np.all((x.reach==5).sum(1)==1)
    assert np.all(x.reach[r,x.champion]==5)
    for conf in ('East','West'):
        cols=[i for i,t in enumerate(x.ids) if x.prep['teams'][t]['conf']==conf]
        assert np.all(np.sort(x.seed[:,cols],axis=1)==np.arange(1,16))
        assert np.all(np.sort(x.playoff_seed[:,cols],axis=1)[:,-8:]==np.arange(1,9))
    for s in x.series:
        if s['stage']!='finals':assert np.all(x.seed[r,s['a']]<x.seed[r,s['b']]),'Conference host must follow original regular rank'
        else:assert np.all(x.wins[r,s['a']]>=x.wins[r,s['b']]),'Finals host has worse regular record'
        events=[e for e in x.events if e['stage']==s['stage'] and f":{s['slot']}:g" in e['id']]
        totals=np.zeros((W,2),int);n=np.zeros(W,int)
        for j,e in enumerate(events):
            active=totals.max(1)<4;assert np.array_equal(active,e['active'])
            a_home=j in (0,1,4,6)
            assert np.array_equal(e['home'],s['a'] if a_home else s['b'])
            assert np.array_equal(e['away'],s['b'] if a_home else s['a'])
            totals[:,0]+=active&(e['winner']==s['a']);totals[:,1]+=active&(e['winner']==s['b']);n+=active
        assert np.all(totals.max(1)==4) and np.array_equal(n,s['length'])
        assert np.array_equal(np.where(totals[:,0]==4,s['a'],s['b']),s['winner'])
    return {'worlds':W,'regular_games_per_world':1230,'regular_games_per_team':82,'cup_events_per_world':67,'playin_per_world':6,'playoff_teams_per_world':16,'series_per_world':15,'champions_per_world':1,'canonical_slots':len(x.events),'negative_OT_proposals_rejected':x.negative_rejections}


def _packed(array):
    return base64.b64encode(np.asarray(array,dtype=np.uint8).tobytes()).decode()


def _save_chunk(task):
    args,target,identity=task;target=Path(target);meta=target.with_suffix('.json')
    if target.exists() or meta.exists():
        if not target.exists() or not meta.exists():raise ValueError('Partial competition receipt; preserve and use fresh namespace')
        old=json.loads(meta.read_text())
        if old['identity']!=identity or old['sha256']!=hashlib.sha256(target.read_bytes()).hexdigest():raise ValueError('Changed competition input/source resume')
        return str(target),True,old['audit']
    x=run_chunk(args);report=audit(x)
    e=x.events
    payload={key:np.stack([r[key] for r in e],axis=1) for key in ('home','away','reg','final','ot','active','winner')}
    payload.update(seed=x.seed,wins=x.wins,playoff_seed=x.playoff_seed,reach=x.reach,cup_rank=x.cup_rank,cup_group=x.cup_group,
                   cup_champion=x.cup_champion,champion=x.champion,
                   series=np.stack([np.stack((s['a'],s['b'],s['winner'],s['length']),1) for s in x.series],1))
    payload['cup_matches']=np.stack([np.stack((r['home'],r['away'],r['winner']),1) for r in e if r['stage'] in ('cup_qf','cup_sf','cup_final')],1)
    event_meta=[{k:v for k,v in r.items() if k in ('id','date','stage','regular','cup','neutral','updated')} for r in e]
    target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_suffix('.tmp.npz');np.savez_compressed(tmp,**payload);os.replace(tmp,target)
    meta.write_text(json.dumps({'identity':identity,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'events':event_meta,'audit':report},sort_keys=True)+'\n')
    return str(target),False,report


def play(T,lg,master,day,teams,engine,W,params=None,weights=None,*,jobs=10,alternative=False,namespace=None):
    """Run/reuse source-guarded canonical1k chunks, then aggregate after pool shutdown."""
    import time
    from scripts.world_mass import WorldMass
    exact_mass=WorldMass(W,weights)
    params={**pathway.PATHWAY,**(params or {}),'competition_schema':rules.SCHEMA}
    started=time.monotonic();prep=prepare(master,teams,day);prep['alternative']=alternative
    sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('scripts/competitions.py','scripts/competition_rules.py','scripts/pathway.py','models/competitions_2026.json')}
    material={'sources':sources,'T':T,'lg':lg,'master':master,'day':day,'W':W,'params':params,'past':prep['past'],'alternative':alternative}
    identity=hashlib.sha256(json.dumps(material,sort_keys=True,default=lambda v:v.tolist()).encode()).hexdigest()
    engine=engine or {}
    if not set(engine).issubset({g['game_id'] for g in master if g['date_et']>=day}):raise ValueError('Engine game outside future calendar')
    if any(np.asarray(v).ndim!=3 or len(v)==0 or np.asarray(v).shape[1]!=2 or np.asarray(v).shape[2]<4 for v in engine.values()):raise ValueError('Invalid engine period arrays')
    engine_hash={k:hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest() for k,v in engine.items()}
    identity=hashlib.sha256((identity+json.dumps(engine_hash,sort_keys=True)).encode()).hexdigest()
    root=Path(namespace) if namespace else ROOT/'data/derived/season_runs'/f'{day}-{identity[:20]}'
    tasks=[]
    for lo in range(0,W,1000):
        n=min(1000,W-lo);selected={k:np.asarray(v)[np.arange(lo,lo+n)%len(v)] for k,v in engine.items()}
        args=(T,lg,prep,selected,n,seed_for(rules.SCHEMA,day,lo//1000),params)
        tasks.append((args,str(root/f'chunk_{lo//1000:05d}.npz'),identity))
    complete={};last=-1
    with ProcessPoolExecutor(max_workers=min(jobs,len(tasks))) as pool:
        pending={pool.submit(_save_chunk,t):i for i,t in enumerate(tasks)}
        for f in as_completed(pending):
            complete[pending[f]]=f.result();mark=10*len(complete)//len(tasks)
            if mark!=last:print(f'competition paths {len(complete)}/{len(tasks)} chunks ({100*len(complete)//len(tasks)}%)',flush=True);last=mark
    # Source mutation invalidates the whole receipt before any publication.
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in sources.items()),'Competition source changed during run'
    chunks=[];receipts=[]
    for i in range(len(tasks)):
        path,reused,report=complete[i];chunks.append(dict(np.load(path,allow_pickle=False)));receipts.append({'path':str(Path(path).relative_to(ROOT)) if Path(path).is_relative_to(ROOT) else path,'reused':reused,'audit':report})
    arrays={k:np.concatenate([c[k] for c in chunks]) for k in chunks[0]}
    metadata=json.loads(Path(tasks[0][1]).with_suffix('.json').read_text())['events']
    # Provider scheduled games retain existing Game Centre regulation distributions.
    remaining=sorted([g for g in master if g['date_et']>=day],key=lambda r:(r['date_et'],r['tip_utc'],r['game_id']))
    by_id={e['id']:j for j,e in enumerate(metadata)}
    gi=[by_id[g['game_id']] for g in remaining]
    home_win=arrays['winner'][:,gi]==arrays['home'][:,gi]
    points=arrays['reg'][:,gi].copy()
    for j,g in enumerate(remaining):
        if g['game_id'] in engine:points[:,j]=arrays['final'][:,gi[j]]
    played={'home_win':home_win,'points':points, 'ids':prep['ids'],'competition_wins':arrays['wins'], 'competition_seed':arrays['seed']}
    mass=np.ones(W,np.int64) if exact_mass.weights is None else exact_mass.weights
    assert mass.shape==(W,) and np.all(mass>0) and int(mass.sum())<=2**53-1
    total=int(mass.sum());mean=lambda x:float(np.sum(np.asarray(x)*mass)/total)
    stages={}
    for i,t in enumerate(prep['ids']):
        stages[t]={'cup_group_winner':mean(arrays['cup_group'][:,i]==1),'cup_qf':mean(arrays['cup_rank'][:,i]<=4),'cup_sf':mean(np.any(arrays['cup_matches'][:,4:6,:2]==i,axis=(1,2))),
         'cup_final':mean(np.any(arrays['cup_matches'][:,6,:2]==i,axis=1)),'cup_title':mean(arrays['cup_champion']==i),
         **{name:mean(arrays['reach'][:,i]>=v) for name,v in (('playoffs',1),('round2',2),('conference',3),('finals',4),('title',5))}}
    package={'schema':rules.SCHEMA,'groups':{name:[prep['ids'][i] for i in v] for name,v in prep['group'].items()},'ids':prep['ids'],'worlds':W,'mass':total,'weights':mass.tolist(),'teams':stages,
             'encoding':'uint8-base64-row-major','paths':{k:_packed(arrays[k]) for k in ('seed','wins','playoff_seed','reach','cup_rank','cup_group','cup_champion','champion','series','cup_matches')},
             'series_slots':[{'stage':s,'slot':j} for s,count in (('round1',8),('round2',4),('conference',2),('finals',1)) for j in range(count)],
             'rules_source':'https://www.nba.com/news/nba-cup-101',
             'assumptions':['2026–27 rules; Cup QF/SF count inside82, neutral final excluded.','Unpublished filler matching approximated: two bottom-finisher cross games,20 within-conference, prefer existing three-game pairs; no travel optimisation. Actual assigned draws replace slots.',
              'Future regulation scores/ratings use unchanged pathway-v1 parameters. Compatible synthetic OT scores are uncalibrated; saved engine finals remain exact. OT period count unavailable for combined engine OT.',
              'Playoff dates use ordered two-day slots and round barriers where unpublished; no rest/travel/injury hazard. Postseason probabilities have no historical calibration claim.',
              'Availability-weighted paths retain original mass; not certified iid season sampling.'],
             'receipt':{'identity':identity,'namespace':str(root.relative_to(ROOT)) if root.is_relative_to(ROOT) else str(root),'chunks':[{k:v for k,v in r.items() if k!='reused'} for r in receipts],'sources':sources}}
    played['competition_execution']={'chunks':receipts,'seconds':round(time.monotonic()-started,3)}
    played['competitions']=package
    return played
