"""Exact S06 selected-timeout decisions composed with accepted NBA Rule3 legality."""
import numpy as np
from scripts.a1_substitution_engine import SelectedTimeoutPolicy,elapsed
from scripts.foul_out import Rule3Policy

class StateRotations(SelectedTimeoutPolicy):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.legal=Rule3Policy(capture_events=True)

    @property
    def technical_events(self):
        return self.legal.technical_events

    def begin(self,g,worlds,available,seed):
        super().begin(g,worlds,available,seed)
        self.legal.begin(g,worlds,available,seed)

    def _legal_plan(self,g,st,w,side,desired):
        desired=np.asarray(desired,dtype=int).copy()
        if (desired.shape!=(5,) or len(set(desired.tolist()))!=5 or
            ((desired<0)|(desired>=g.n)).any() or (g.side[desired]!=side).any()):
            raise ValueError('state rotation requires distinct five teammates')
        allowed=(g.side==side)&self.available[w]&((st.ingame['pf_so_far'][w]<6)|self.legal.exempt[w])
        if allowed.sum()<5:raise ValueError('state rotation has fewer than five Rule3-eligible players')
        for slot in np.flatnonzero(~allowed[desired]):
            bench=np.flatnonzero(allowed&~np.isin(np.arange(g.n),desired))
            if not len(bench):raise ValueError('state rotation has no legal replacement')
            desired[slot]=bench[np.argmax(g.expected[bench])]
        return desired

    def before_segment(self,g,st,active,scheduled):
        scheduled=self.legal.before_segment(g,st,active,scheduled)
        return super().before_segment(g,st,active,scheduled)

    def after_fouls(self,g,st,active,offense,defense):
        changed=self.legal.after_fouls(g,st,active,offense,defense)
        off=st.off[active]
        for row in np.flatnonzero(changed):
            w=int(active[row]);now=float(elapsed(st.period[w:w+1],st.clock[w:w+1])[0])
            for side,five in ((int(off[row]),offense[row]),(1-int(off[row]),defense[row])):
                self._set(g,st,w,side,five,now)
        self.counts.update({'rule3_'+k:v for k,v in self.legal.counts.items()})
        return changed

    def finish(self,g,st):
        super().finish(g,st)
        self.legal.finish(g,st)
