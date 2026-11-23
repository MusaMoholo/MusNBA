import gzip
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import export_musnba, nightly_musnba


class BundleProfilesTests(unittest.TestCase):
    def test_phone_and_laptop_preserve_their_world_contracts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            api = root / 'views' / 'api'
            (api / 'game' / '123').mkdir(parents=True)
            (api / 'slate').mkdir()
            logos = root / 'logos'
            logos.mkdir()
            icons = root / 'player-icons'
            icons.mkdir()
            (icons / '1.png').write_bytes(b'retained-photo-fixture')
            files = {
                api / 'meta.json': {'latest': '2026-11-22', 'snapshots': [{'date': '2026-11-22'}], 'player_icons': {'ids': ['1']}},
                api / 'players.json': {'players': []},
                api / 'game' / '123.json': {'worlds': True, 'minute_marginals': True},
                api / 'game' / '123' / 'worlds.json': {'worlds': 2, 'players': ['1']},
                api / 'game' / '123' / 'minute-marginals.json': {'schema': 1},
                api / 'slate' / '2026-11-22.json': {'games': [{'proj': {'duel': {'id': 1}}}]},
            }
            for path, data in files.items():
                path.write_text(json.dumps(data))
            results = {}
            with patch.object(export_musnba, 'VIEWS', root / 'views'), patch.object(export_musnba, 'LOGOS', logos), patch.object(export_musnba, 'PLAYER_ICONS', icons), patch.object(export_musnba, 'player_icons', return_value={'ids': ['1']}):
                for profile in ('phone', 'laptop'):
                    output = root / f'{profile}.musnba.gz'
                    export_musnba.export_bundle(output, profile=profile)
                    with gzip.open(output, 'rt') as stream:
                        rows = [json.loads(line) for line in stream]
                    results[profile] = (rows[0], {r['key']: r for r in rows[1:-1]})
            phone, laptop = results['phone'], results['laptop']
            self.assertEqual(phone[0]['version'], 2)
            self.assertIn('player-icons-v1', phone[0]['capabilities'])
            self.assertTrue(phone[1]['/player-icons/1.png']['binary'])
            self.assertEqual(phone[1]['/player-icons/1.png'], laptop[1]['/player-icons/1.png'])
            self.assertEqual(phone[0]['profile'], 'phone')
            self.assertEqual(laptop[0]['profile'], 'laptop')
            self.assertNotIn('/api/game/123/worlds', phone[1])
            self.assertEqual(json.loads(phone[1]['/api/game/123']['body'])['worlds'], False)
            self.assertTrue(json.loads(phone[1]['/api/game/123']['body'])['minute_marginals'])
            self.assertIn('/api/game/123/minute-marginals', phone[1])
            self.assertNotIn('/api/game/123/minute-marginals', laptop[1])
            self.assertNotIn('duel', json.loads(phone[1]['/api/slate/2026-11-22']['body'])['games'][0]['proj'])
            for key, path in (('/api/game/123', api / 'game' / '123.json'),
                              ('/api/game/123/worlds', api / 'game' / '123' / 'worlds.json'),
                              ('/api/slate/2026-11-22', api / 'slate' / '2026-11-22.json')):
                self.assertEqual(laptop[1][key]['body'], path.read_text())

    def test_laptop_name_is_derived_from_custom_phone_destination(self):
        self.assertEqual(nightly_musnba.laptop_output(Path('/tmp/custom.musnba.gz')),
                         Path('/tmp/custom-laptop.musnba.gz'))

    def test_export_failure_stops_before_updating_phone(self):
        argv = ['nightly_musnba.py', '--export-only', '--output', '/tmp/custom.musnba.gz']
        with patch('sys.argv', argv), patch.object(nightly_musnba, 'check_output_access') as access, \
             patch.object(nightly_musnba, 'view_inventory', return_value={}), \
             patch.object(nightly_musnba.subprocess, 'run', return_value=SimpleNamespace(returncode=1)) as run:
            self.assertEqual(nightly_musnba.main(), 1)
        self.assertEqual(access.call_count, 2)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][-2:], ['--profile', 'laptop'])

    def test_changed_views_stop_before_phone_export(self):
        argv = ['nightly_musnba.py', '--export-only', '--output', '/tmp/custom.musnba.gz']
        with patch('sys.argv', argv), patch.object(nightly_musnba, 'check_output_access'), \
             patch.object(nightly_musnba, 'view_inventory', side_effect=[{'one': (1, 1)}, {'one': (2, 2)}]), \
             patch.object(nightly_musnba.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as run:
            self.assertEqual(nightly_musnba.main(), 1)
        self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
