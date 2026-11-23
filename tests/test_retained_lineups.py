import tempfile
import unittest
from pathlib import Path

import numpy as np

from basketball_common import write_json
from scripts import nightly


class RetainedLineupTests(unittest.TestCase):
    def test_weighted_branches_keep_original_mass_and_replay_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'2026-11-22'
            fixture = {'game_id':'a','home_id':'1','away_id':'2','status':'scheduled',
                       'time_valid':'1','tip_utc':'2026-11-22T18:00:00Z'}
            completed = '2026-11-22T18:30:00Z'
            model = {'id':'fixture','sims':1}
            meta = {'kind':'prospective','slate_date':target.name,'origin':target.name,'model':model,
                    'sims':1,'saved_worlds':{'a':2},'games':['a'],'pre_tip':{'a':True},
                    'completed_at':'2026-11-22T17:00:00Z'}
            game = {'game_id':'a','model':'fixture','sims':2,'probability_mass':10,'lineups':{'worlds_per_branch':1},
                    'home':{'team_id':'1'},'away':{'team_id':'2'},
                    'periods':{'fg':{'home':{'pts':{'mean':.7},'win':.7},'away':{'pts':{'mean':.3}}}}}
            points = np.zeros((2,2,5),np.int16)
            points[0,0,0] = points[1,1,0] = 1
            lines = np.zeros((2,2,2),np.uint8)
            lines[:,:,1] = points.sum(2)
            stats = {'teams':{},'league':{},'players':{}}
            write_json(target/'meta.json',meta)
            write_json(target/'games.json',{'a':game})
            write_json(target/'games_placeholder.json',{'a':{'placeholder':True}})
            write_json(target/'stats.json',stats)
            write_json(target/'lineups/a/provenance.json',{'retained':True})
            np.savez(target/'engine_worlds.npz',a=points)
            np.savez(target/'engine_players.npz',a__ids=np.array(['h','v']),a__side=np.array([0,1]),
                     a__lines=lines,a__weights=np.array([7,3]))
            saved = nightly.load_retained(target,[fixture],completed)
            self.assertEqual(saved['a']['live_dir'],target/'lineups/a')
            self.assertEqual(saved['a']['game'],game)
            indices = np.array([0,1,0])
            part = {'slate':[fixture],'prospective':True,'origin':target.name,'model':model,'sims':1,
                    'T':{},'lg':{},'P':{},'retained':saved,'games':{'a':game},
                    'placeholder':{'a':{'placeholder':True}},'worlds':{'a':points},
                    'player_worlds':{'a':saved['a']['players']},'season_worlds':{'a':points[indices]},
                    'season_indices':{'a':indices},'season_weights':np.array([3,3,4])}
            season = {'sims':3,'games':[{'game_id':'a','source':'engine','p_home':.7,'mu_home':.7,'mu_away':.3}]}
            nightly.validate_retained(part,season,target,completed)
            part['season_weights'] = np.array([2,4,4])
            with self.assertRaisesRegex(ValueError,'probability masses differ'):
                nightly.validate_retained(part,season,target,completed)
            part['season_weights'] = np.array([3,3,4])
            part['season_worlds']['a'] = np.zeros_like(points[indices])
            with self.assertRaisesRegex(ValueError,'world identities differ'):
                nightly.validate_retained(part,season,target,completed)


if __name__ == '__main__':
    unittest.main()
