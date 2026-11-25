"""Read-only exact zone counts and selected-world segment records; never draws randomness."""
import numpy as np

SCHEMA='visible-worlds-v1'
class WorldDetail:
    def __init__(self,selected=(),capture_rotations=True):
        self.selected=tuple(sorted(set(map(int,selected))))
        self.capture_rotations=capture_rotations

    def begin(self,g,st):
        if any(w<0 or w>=st.W for w in self.selected):raise ValueError('selected world outside original full chunk')
        self.attempts=np.zeros((st.W,g.n,5,5),dtype=np.uint16)
        self.makes=np.zeros_like(self.attempts)
        self.events={w:[] for w in self.selected};self.before={}
        if self.capture_rotations:
            self.rotation_presence=np.zeros((st.W,g.n,48),dtype=np.uint8)
            self.rotation_seen=np.zeros((st.W,48),dtype=bool)

    def before_segment(self,g,st,active,lineups):
        self.before={}
        if self.capture_rotations:
            self.rotation_period=st.period[active].copy()
            self.rotation_clock=st.clock[active].copy()
        selected=np.flatnonzero(np.isin(active,self.selected))
        for row in selected:
            w=int(active[row])
            self.before[w]={'period':int(st.period[w]),'clock':float(st.clock[w]),'score':st.score[w].astype(int).tolist(),
                'minutes':st.minutes[w].sum(1).copy(),'box':{k:v[w].sum(1).copy() for k,v in st.box.items()}}

    def after_segment(self,g,st,active,record):
        if self.capture_rotations:
            start=(self.rotation_period-1)*720+720-self.rotation_clock
            action=(self.rotation_period-1)*720+720-(self.rotation_clock-record['secs'])
            end=(self.rotation_period-1)*720+720-st.clock[active]
            after=np.empty_like(record['lineups'])
            rows=np.arange(len(active));off=record['off']
            after[rows,off]=record['offense'];after[rows,1-off]=record['defense']
            ticks=np.arange(30,2880,60)
            for lo,hi,fives in ((start,action,record['lineups']),(action,end,after)):
                r,t=np.nonzero((ticks>=lo[:,None])&(ticks<hi[:,None])&(self.rotation_period[:,None]<=4))
                worlds=active[r]
                if self.rotation_seen[worlds,t].any():raise ValueError('duplicate rotation time capture')
                self.rotation_seen[worlds,t]=True
                self.rotation_presence[worlds[:,None],fives[r].reshape(-1,10),t[:,None]]=1
        shots=record['shot'];made=shots[record['res'][shots]>=1]
        pidx=np.minimum(st.period[active]-1,4)
        for values,rows in ((self.attempts,shots),(self.makes,made)):
            np.add.at(values,(active[rows],record['actor'][rows],pidx[rows],record['zone'][rows]),1)
        for row in np.flatnonzero(np.isin(active,self.selected)):
            w=int(active[row]);before=self.before[w]
            lineups=np.empty((2,5),int);off=int(record['off'][row])
            lineups[off]=record['offense'][row];lineups[1-off]=record['defense'][row]
            credits=[]
            for key,array in st.box.items():
                delta=array[w].sum(1).astype(np.int64)-before['box'][key].astype(np.int64)
                if (delta<0).any():raise ValueError('captured box credit decreased')
                credits.extend([g.ids[int(i)],key,int(delta[i])] for i in np.flatnonzero(delta))
            seconds=(st.minutes[w].sum(1)-before['minutes'])*60
            if (seconds<-1e-9).any():raise ValueError('captured minutes decreased')
            ids=lambda indices:[[str(g.ids[int(i)]) for i in five] for five in indices]
            event={'period':before['period'],'before_clock':before['clock'],
                'action_clock':before['clock']-float(record['secs'][row]),'after_clock':float(st.clock[w]),
                'offense':off,'score_before':before['score'],'score_after':st.score[w].astype(int).tolist(),
                'lineups':ids(record['lineups'][row]),'lineups_after':ids(lineups),'credits':credits,
                'seconds':[[str(g.ids[int(i)]),float(seconds[i])] for i in np.flatnonzero(seconds)]}
            if row in shots:
                event['shot']={'player':str(g.ids[int(record['actor'][row])]),'zone':int(record['zone'][row]),
                               'band':int(record['band'][row]),'made':bool(record['res'][row]>=1),'value':3 if record['zone'][row]>=3 else 2}
            self.events[w].append(event)

    def finish(self,g,st):
        for stat,values in [('fga',self.attempts),('fgm',self.makes)]:
            if not np.array_equal(values.sum(3),st.box[stat]):raise ValueError(f'{stat}: exact zone/player/period totals differ')
        if (self.makes>self.attempts).any():raise ValueError('zone makes exceed attempts')
        for stat,values in [('fg3a',self.attempts),('fg3m',self.makes)]:
            if not np.array_equal(values[:,:,:,3:].sum(3),st.box[stat]):raise ValueError('zone three-point totals differ')
        if not st.done.all():raise ValueError('detail capture requires all original worlds to finish')
        if self.capture_rotations:
            if not self.rotation_seen.all():raise ValueError('missing regulation rotation time')
            for side in (0,1):
                if not (self.rotation_presence[:,g.side==side].sum(1)==5).all():raise ValueError('rotation capture must have five per team/time')
        # This independent reconstruction trusts neither engine package summaries nor UI accumulation.
        self.audit={}
        for w,events in self.events.items():
            boxes={key:np.zeros(g.n,np.int64) for key in st.box};seconds=np.zeros(g.n);lookup={pid:i for i,pid in enumerate(g.ids)}
            previous=[0,0];period=1;clock=720.;stint_seconds=np.zeros(g.n)
            for e in events:
                if e['period']<period or (e['period']==period and e['before_clock']!=clock):raise ValueError('segment period/clock gap')
                if e['period']>period and (e['period']!=period+1 or e['before_clock']!=(720 if e['period']<=4 else 300)):raise ValueError('invalid period transition')
                if not 0<=e['after_clock']<=e['action_clock']<=e['before_clock']:raise ValueError('invalid captured segment clocks')
                if e['score_before']!=previous:raise ValueError('segment score discontinuity')
                for fives,a,b in [(e['lineups'],e['before_clock'],e['action_clock']),
                                  (e['lineups_after'],e['action_clock'],e['after_clock'])]:
                    for side,five in enumerate(fives):
                        indices=[lookup[pid] for pid in five]
                        if len(indices)!=5 or len(set(indices))!=5 or (g.side[indices]!=side).any():raise ValueError('captured lineup is not a distinct teammate five')
                        stint_seconds[indices]+=a-b
                for pid,key,amount in e['credits']:boxes[key][lookup[pid]]+=amount
                for pid,value in e['seconds']:seconds[lookup[pid]]+=value
                previous=e['score_after'];period=e['period'];clock=e['after_clock']
            for key,array in st.box.items():
                if not np.array_equal(boxes[key],array[w].sum(1)):raise ValueError('replayed player box differs')
            error=float(np.max(np.abs(seconds/60-st.minutes[w].sum(1))))
            if not np.allclose(stint_seconds,seconds,rtol=0,atol=1e-6):raise ValueError('lineup/clock reconstruction differs from recorded player minutes')
            if error>1e-8 or previous!=st.score[w].astype(int).tolist():raise ValueError('replayed seconds/final score differs')
            self.audit[w]={'segments':len(events),'max_minute_error':error,'all_box_fields_exact':True,'final_score_exact':True}
