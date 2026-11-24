"""Research-only prior-fitted long shots on short end-of-period possessions."""
from datetime import date
import numpy as np
from scripts import nodes, projection


class BuzzerShots:
    def __init__(self, recipe):
        if recipe['kind'] != 'b1-buzzer-shots-v1':
            raise ValueError('unknown buzzer recipe')
        self.cutoff = date.fromisoformat(recipe['train_through'])
        if date.fromisoformat(recipe['latest_training_date']) > self.cutoff:
            raise ValueError('future buzzer parameters')
        self.recipe = recipe
        self.starts = [nodes.START_TYPES.index(x) for x in recipe['routing']['start_types']]
        self.inbound = [nodes.START_TYPES.index(x) for x in ('made_fg', 'made_ft')]
        self.distance = np.asarray(recipe['geometry']['distance'], dtype=np.float32)
        self.lateral = np.asarray(recipe['geometry']['lateral'], dtype=np.float32)
        if (self.distance.ndim != 1 or len(self.distance) < 100 or self.distance.shape != self.lateral.shape
                or not np.isfinite(self.distance).all() or not np.isfinite(self.lateral).all()
                or (self.distance < 40).any() or (self.lateral < 0).any()):
            raise ValueError('invalid prior long-shot geometry')
        probabilities = [c['probability'] for c in recipe['routing']['cells'].values()]
        probabilities.append(recipe['conversion']['probability'])
        if any(not np.isfinite(p) or not 0 <= p <= 1 for p in probabilities):
            raise ValueError('invalid long-shot probabilities')

    def begin(self, origin, seed):
        if date.fromisoformat(origin) <= self.cutoff:
            raise ValueError('buzzer parameters must precede origin')
        self.rng = np.random.default_rng(projection.seed_for('b1-buzzer-v1', int(seed)))
        self.counts = {'eligible_shots': 0, 'routed_long_shots': 0, 'long_makes': 0}

    def select(self, context, what):
        routing = self.recipe['routing']
        start, elapsed = context['start_clock'], context['shot_time']
        eligible = ((what >= 0) & (what < len(nodes.ZONES)) & (start <= routing['start_clock_max'])
                    & (start - elapsed <= routing['action_clock_max'])
                    & np.isin(context['start_code'], self.starts))
        selected = np.zeros(len(what), dtype=bool)
        rows = np.flatnonzero(eligible)
        self.counts['eligible_shots'] += len(rows)
        if len(rows):
            cells = routing['cells']
            probability = np.where(np.isin(context['start_code'][rows], self.inbound),
                                    cells['inbound']['probability'], cells['change']['probability'])
            selected[rows] = self.rng.random(len(rows)) < probability
        self.counts['routed_long_shots'] += int(selected.sum())
        self.selected = selected
        return selected

    def locations(self, shot, band, distance, lateral):
        """Keep existing coarse above3 band for stored maps, retain actual fitted numeric geometry."""
        rows = np.flatnonzero(self.selected[shot])
        if len(rows):
            draws = self.rng.integers(len(self.distance), size=len(rows))
            band[rows] = nodes.LOCATION_BANDS - 1
            distance[rows], lateral[rows] = self.distance[draws], self.lateral[draws]
        return band, distance, lateral

    def results(self, shot, results):
        rows = np.flatnonzero(self.selected[shot])
        if len(rows):
            hit = self.rng.random(len(rows)) < self.recipe['conversion']['probability']
            results[rows] = hit.astype(int)
            self.counts['long_makes'] += int(hit.sum())
        return results
