"""Research-only vectorized version of the audited matched foul-penalty continuation."""
from __future__ import annotations

import numpy as np

from analysis import a1_matched_penalty_repair as matched
from scripts import a1_branch_foul_out


class VectorContinuationRepair(matched.ContinuationRepair):
    def begin(self, g, worlds, available, seed):
        a1_branch_foul_out.BranchFoulOutPolicy.begin(self, g, worlds, available, seed)
        self.exempt = np.zeros_like(available)


class VectorMatchedPenaltyTrace(matched.MatchedPenaltyTrace):
    def __init__(self):
        super().__init__()
        self.repair = VectorContinuationRepair()
