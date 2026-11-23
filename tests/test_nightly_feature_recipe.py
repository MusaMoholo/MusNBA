import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import engine, features, nightly, possessions, rotations


class NightlyFeatureRecipeTests(unittest.TestCase):
    def rebuild(self, root, runtime):
        with patch.object(nightly, 'ROOT', root), patch.object(nightly, 'DERIVED', root/'data/derived'), \
                patch.object(engine, 'ENGINE', runtime), \
                patch.object(possessions, 'build_current', return_value={'games':1,'segments':100,'games_flagged':0}), \
                patch.object(possessions, 'current_games', return_value=[]), \
                patch.object(rotations, 'build', return_value={'stints':4}), \
                patch.object(features, 'build', return_value={'player_games':20}) as build:
            result = nightly.rebuild_engine_inputs('2026-11-23')
        return result, build.call_args_list

    def test_runtime_alias_rebuilds_the_fitted_models_profile_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'models').mkdir()
            (root/'models/v1.3.json').write_text(json.dumps({'features_variant':{
                'out':'data/derived/variants/matchup/features','defence':True,'shot_types':True}}))
            # Runtime aliases have no separate node/feature recipe.
            for version in ('v1.3-r1','v1.3-r2','v1.3-r3'):
                with self.subTest(version=version):
                    result,calls=self.rebuild(root,{'version':version,'models':'v1.3'})
                    self.assertEqual(result['games'],1)
                    self.assertEqual(len(calls),2)
                    self.assertEqual(calls[1].args,(root/'data/derived/variants/matchup/features',))
                    self.assertTrue(calls[1].kwargs['defence'])
                    self.assertTrue(calls[1].kwargs['shot_types'])

    def test_missing_fitted_recipe_cannot_silently_skip_required_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                self.rebuild(Path(tmp),{'version':'v1.3-r1','models':'missing'})


if __name__=='__main__':
    unittest.main()
