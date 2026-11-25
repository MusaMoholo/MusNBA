"""Research-only historical regular paths sharing accepted C5 score/update mechanics."""
from unittest.mock import patch
import numpy as np
from scripts import competitions,competition_rules as rules,pathway,projection
from analysis.b2_calendar_audit import POLICIES


class HistoricalPaths(competitions.Paths):
    def __init__(self,frame,metadata,day,start,teams,periods,previous_wins,worlds,seed,params):
        year=metadata['season'];self.year=year;self.calendar=POLICIES[year]
        ids=sorted(teams,key=int);index={t:i for i,t in enumerate(ids)}
        group_ids=set(metadata.get('group_game_ids',[]))
        fixtures=[];past={}
        for row in frame[frame.home].sort_values(['date','game_id']).itertuples():
            game={'game_id':str(row.game_id),'home_id':row.team,'away_id':row.opp,'date_et':row.date,
                  'neutral':int(row.neutral),'notes':'Group Play' if str(row.game_id) in group_ids else ''}
            fixtures.append(game)
            if row.date<day:
                original=periods.loc[str(row.game_id)]
                reg=[int(original.reg_home),int(original.reg_away)]
                full=[int(row.pts),int(row.opp_pts)]
                past[str(row.game_id)]={'reg':reg,'final':full,'ot':int(original.ot)}
                if [int(original.final_home),int(original.final_away)]!=full or (reg[0]==reg[1])!=(original.ot>0):
                    raise ValueError('historical regulation/OT source mismatch')
        self.unresolved=bool(metadata['removed_final'] and day<f'{year-1}-{self.calendar["window"][0]}')
        if self.unresolved:
            lo,hi=[f'{year-1}-{md}' for md in self.calendar['window']]
            fixtures=[g for g in fixtures if not lo<=g['date_et']<=hi]
        groups={}
        for j,group in enumerate(metadata['groups']):
            conf=teams[group[0]]['conf']
            if any(teams[t]['conf']!=conf for t in group):raise ValueError('historical group crosses conferences')
            groups[f'{conf} {j}']=[index[t] for t in group]
        pairs=np.zeros((30,30),int)
        for game in fixtures:
            h,a=index[game['home_id']],index[game['away_id']];pairs[h,a]+=1;pairs[a,h]+=1
        prepared={'ids':ids,'group':groups,'base':fixtures,'actual':[],'pairs':pairs,'past':past,
                  'policy':{'prior_regular_wins':previous_wins},'day':day,'teams':teams}
        def fitted(*unused):
            return tuple(np.asarray(start[k],float) for k in ('off','def','pace','gp'))
        rng=np.random.default_rng(projection.seed_for('b2-paths-v1',day,seed))
        aux=np.random.default_rng(projection.seed_for('b2-paths-aux-v1',day,seed))
        with patch.object(pathway,'start_ratings',side_effect=fitted):
            super().__init__(start['T'],start['league'],prepared,worlds,rng,aux,params=params)
        future=frame[frame.date.ge(day)&frame.home].sort_values(['date','game_id'])
        self.split=str(future.date.iloc[len(future)//2])
        self.remaining_points=np.zeros((worlds,30),np.int32)
        self.first_wins=np.zeros((worlds,30),np.uint8)
        self.known_hist={}

    def event(self,*args,**kwargs):
        output=super().event(*args,**kwargs);event=self.events[-1]
        if event['stage']=='group' and self.calendar.get('cup_tiebreak_points')=='full_game':
            extra=event['final']-event['reg'];h,a=event['home'],event['away'];r=self.rows
            self.cd[r,h]+=extra[:,0]-extra[:,1];self.cd[r,a]+=extra[:,1]-extra[:,0]
            self.cp[r,h]+=extra[:,0];self.cp[r,a]+=extra[:,1]
        if event['regular'] and event['date']>=self.prep['day']:
            h,a=event['home'],event['away'];r=self.rows;points=event['final']
            self.remaining_points[r,h]+=points[:,0];self.remaining_points[r,a]+=points[:,1]
            if event['date']<self.split:self.first_wins[r,event['winner']]+=1
            if kwargs.get('provider') is not None:
                maximum=int(points.max())+1
                self.known_hist[event['id']]=np.stack([np.bincount(points[:,s],minlength=maximum) for s in (0,1)]).astype(np.uint16)
        return output

    def cup(self):
        """Historical neutral semifinal bracket; no actual future Cup assignments are read."""
        W=self.W;previous=np.array([self.prep['policy']['prior_regular_wins'][t] for t in self.ids]);draw=self.aux.random((W,30))
        qualifiers=np.zeros((W,8),np.uint8);non=[np.zeros((W,11),np.uint8),np.zeros((W,11),np.uint8)]
        self.cup_rank=np.zeros((W,30),np.uint8)
        for w in range(W):
            for ci,conf in enumerate(('East','West')):
                ranked=[rules.cup_order(tids,self.cw[w],self.chw[w],self.chn[w],self.cd[w],self.cp[w],previous,draw[w])
                        for name,tids in self.prep['group'].items() if name.startswith(conf)]
                winners=rules.cup_order([v[0] for v in ranked],self.cw[w],self.chw[w],self.chn[w],self.cd[w],self.cp[w],previous,draw[w],False)
                wildcard=rules.cup_order([v[1] for v in ranked],self.cw[w],self.chw[w],self.chn[w],self.cd[w],self.cp[w],previous,draw[w],False)[0]
                q=winners+[wildcard];qualifiers[w,ci*4:ci*4+4]=q
                rest=rules.cup_order([t for v in ranked for t in v if t not in q],self.cw[w],self.chw[w],self.chn[w],self.cd[w],self.cp[w],previous,draw[w],False)
                non[ci][w]=rest;self.cup_rank[w,q+rest]=np.arange(1,16)
        filler=np.stack([rules.fillers([list(x[w]) for x in non],self.prep['pairs']) for w in range(W)])
        qf=[];losers=[];was_home=[];year=self.year-1
        for ci in range(2):
            for j,(u,v) in enumerate(((0,3),(1,2))):
                h,a=qualifiers[:,4*ci+u],qualifiers[:,4*ci+v]
                win,lose=self.event(f'b2:{year}:qf:{ci}:{j}',f'{year}-{self.calendar["qf"][ci]}','cup_qf',h,a)
                qf.append(win);losers.append(lose);was_home.append(lose==h)
        finalists=[]
        # Each nonqualifier round and QF-loser pairing lies in the season-specific published Cup window.
        for round_,md in enumerate(self.calendar['filler']):
            date=f'{year}-{md}'
            if round_==1:
                for ci in range(2):
                    a,b=qf[2*ci:2*ci+2];higher=self.cup_rank[self.rows,a]<self.cup_rank[self.rows,b]
                    h,away=np.where(higher,a,b),np.where(higher,b,a)
                    win,_=self.event(f'b2:{year}:sf:{ci}',f'{year}-{self.calendar["sf"]}','cup_sf',h,away,True)
                    finalists.append(win)
            for j in range(11):self.event(f'b2:{year}:filler:{round_}:{j}',date,'filler',filler[:,round_,j,0],filler[:,round_,j,1])
            if round_==1:
                for ci in range(2):
                    a,b=losers[2*ci:2*ci+2];host=was_home[2*ci]<=was_home[2*ci+1]
                    self.event(f'b2:{year}:qf-losers:{ci}',date,'filler',np.where(host,a,b),np.where(host,b,a))
        self.event(f'b2:{year}:cup-final',f'{year}-{self.calendar["window"][1]}','cup_final',finalists[0],finalists[1],True)

    def regular(self):
        if self.unresolved:
            lo,hi=[f'{self.year-1}-{md}' for md in self.calendar['window']]
            before=[g for g in self.prep['base'] if g['date_et']<lo]
            after=[g for g in self.prep['base'] if g['date_et']>hi]
        else:before,after=self.prep['base'],[]
        def play(games):
            for g in games:self.event(g['game_id'],g['date_et'],'group' if g['notes'] else 'regular',
                self.index[g['home_id']],self.index[g['away_id']],bool(g['neutral']),provider=g)
        play(before)
        if self.unresolved:self.cup()
        play(after)
        if not np.all(self.gp==82) or not np.all(self.wins.sum(1)==1230):raise ValueError('regular calendar not82/team/1230 wins')
        if self.past_applied!=set(self.prep['past']):raise ValueError('past game omitted or duplicated')

    def capture(self):
        self.regular();gp=np.zeros_like(self.gp);wins=np.zeros_like(self.wins);points=np.zeros_like(self.remaining_points)
        seen=set();last=''
        for e in self.events:
            if e['id'] in seen or e['date']<last:raise ValueError('event chronology/identity')
            seen.add(e['id']);last=e['date'];h,a=e['home'],e['away'];r=self.rows
            if np.any(h==a) or np.any(e['final']<e['reg']) or np.any(e['final'][:,0]==e['final'][:,1]):raise ValueError('invalid event scores')
            if e['regular']:
                gp[r,h]+=1;gp[r,a]+=1;wins[r,e['winner']]+=1
                if e['date']>=self.prep['day']:
                    points[r,h]+=e['final'][:,0];points[r,a]+=e['final'][:,1]
        if not np.array_equal(gp,self.gp) or not np.array_equal(wins,self.wins) or not np.array_equal(points,self.remaining_points):
            raise ValueError('independent event accounting failed')
        ids=sorted(self.known_hist);maximum=max(h.shape[1] for h in self.known_hist.values())
        hist=np.stack([np.pad(self.known_hist[gid],((0,0),(0,maximum-self.known_hist[gid].shape[1]))) for gid in ids])
        return {'wins':self.wins,'remaining_points':self.remaining_points,'first_wins':self.first_wins,
                'known_ids':np.asarray(ids),'known_hist':hist}, {'worlds':self.W,'games_per_team':82,'wins_per_world':1230,
                'events':len(self.events),'known_future_games':len(ids),'unresolved_cup':self.unresolved,
                'past_events':len(self.past_applied),'negative_ot_proposals_rejected':self.negative_rejections}
