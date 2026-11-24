import unittest
import numpy as np
from scripts import court_zones as z,nodes,court_profiles as profiles
from scripts.court_runtime import CourtRuntime,SCHEMA


def auxiliary(variant):
    spec=z.layout(variant!='zone');coarse,cell,mask=z.decoder(spec)
    compat=nodes.LOCATION_MASK[coarse].astype(float)
    compat/=compat.sum(axis=1,keepdims=True)
    return {'schema':SCHEMA,'variant':variant,'layout':spec,'training_through':'2025-12-31',
            'latest_fit_date':'2025-10-01','distance':[10.]*len(cell),'lateral':[3.]*len(cell),
            'compatibility_band_probabilities':compat.tolist() if variant=='zone' else None}


class CourtRuntimeTest(unittest.TestCase):
    def test_decoder_preserves_value_and_selected_player_prior(self):
        for variant in ['zone','distance','defence']:
            court=CourtRuntime(auxiliary(variant),'2025-12-31');n=len(court.cell)
            actor={f'actor_court_fg_{i}':np.full(n,i/22) for i in range(22)}
            band,extra=court.decode(np.arange(n),actor,np.random.default_rng(11))
            coarse=np.argmax(nodes.LOCATION_MASK[:,band],axis=0)
            np.testing.assert_array_equal(coarse,court.coarse)
            np.testing.assert_allclose(extra['actor_court_fg_selected'],court.cell/22,rtol=1e-6)
            self.assertEqual('distance' in extra,variant!='zone')

    def test_distance_decoder_consumes_no_extra_random_draw(self):
        court=CourtRuntime(auxiliary('distance'),'2025-12-31')
        rng=np.random.default_rng(7);before=rng.bit_generator.state
        court.decode(np.array([0]),{f'actor_court_fg_{i}':np.array([.5]) for i in range(22)},rng)
        self.assertEqual(before,rng.bit_generator.state)

    def test_missing_defender_remains_missing(self):
        court=CourtRuntime(auxiliary('defence'),'2025-12-31')
        cols=profiles.COLS[44:88]+[f'court_d_rate_{i}' for i in range(22)]
        P={col:np.array([np.nan,.1,.2,.3,.4,.5],np.float32) for col in cols}
        context=court.context(P,np.array([[0,1,2,3,4],[1,2,3,4,5]]))
        for value in context.values():self.assertTrue(np.isnan(value[0]));self.assertAlmostEqual(value[1],.3,places=6)

    def test_future_auxiliary_and_wrong_cutoff_fail(self):
        aux=auxiliary('zone')
        with self.assertRaises(ValueError):CourtRuntime(aux,'2023-12-31')
        aux['latest_fit_date']='2026-01-01'
        with self.assertRaises(ValueError):CourtRuntime(aux,'2025-12-31')
        aux=auxiliary('zone');aux['compatibility_band_probabilities'][0]=[1.]*nodes.LOCATION_BANDS
        with self.assertRaises(ValueError):CourtRuntime(aux,'2025-12-31')

if __name__=='__main__':unittest.main()
