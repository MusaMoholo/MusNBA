import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.late_clock import load_recipe


class ClockRecipeTests(unittest.TestCase):
    def recipe(self):
        return {'kind': 'contextual-clock-v1', 'train_through': '2026-06-30',
                'training': {'cutoff': '2026-06-30', 'latest_training_date': '2026-06-22', 'cells': {}},
                'pools': {'bridge': {'20': {'x': [2., 24.], 'quiet': .5}}, 'contextual': {}}}

    def test_loaded_parameters_cannot_cross_origin(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'clock.json'
            path.write_text(json.dumps(self.recipe()))
            policy = load_recipe(path, '2026-06-30')
            policy.check_origin('2026-07-01')
            for origin in ('2026-06-30', '2026-06-29', 'invalid'):
                with self.assertRaises(ValueError):
                    policy.check_origin(origin)

    def test_inconsistent_fit_metadata_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'clock.json'
            for section, key, value in ((None, 'train_through', '2026-07-01'),
                                        ('training', 'cutoff', '2026-07-01'),
                                        ('training', 'latest_training_date', '2026-07-01')):
                recipe = self.recipe()
                (recipe if section is None else recipe[section])[key] = value
                path.write_text(json.dumps(recipe))
                with self.assertRaises(ValueError):
                    load_recipe(path, '2026-06-30')

    def test_backtest_preflight_rejects_late_parameters_before_starting_workers(self):
        from scripts import backtest, engine
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'fold').mkdir()
            (root / 'fold/config.json').write_text(json.dumps({'train_through': '2025-12-31'}))
            path = root / 'clock.json'
            path.write_text(json.dumps(self.recipe()))
            with patch.object(engine, 'MODELS', root):
                with self.assertRaisesRegex(ValueError, 'pass --clock-recipe'):
                    backtest.clock_runtime('fold', path)
                recipe = self.recipe()
                recipe.update(train_through='2025-12-31')
                recipe['training'].update(cutoff='2025-12-31', latest_training_date='2025-12-30')
                path.write_text(json.dumps(recipe))
                runtime = backtest.clock_runtime('fold', path)
                self.assertEqual(runtime['clock_recipe'], str(path.resolve()))
                self.assertEqual(runtime['rotation_fit'], engine.ENGINE['rotation_fit'])


if __name__ == '__main__':
    unittest.main()
