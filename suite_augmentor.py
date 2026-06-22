"""
suite_augmentor.py
Augments non-revealing suites adequate for A to also satisfy B,
then checks for fault revelation.
"""

import random
from models import CoverageData
from coverage_engine import is_adequate, is_revealing, get_max_pool_coverage, get_suite_coverage


def _greedy_augment(data, criterion_b, initial_suite, candidate_tests, rng):
    max_cov_b = get_max_pool_coverage(data, criterion_b)
    cov_map   = data.coverage.get(criterion_b, {})
    suite     = set(initial_suite)
    covered   = get_suite_coverage(data, criterion_b, suite)
    remaining = max_cov_b - covered
    pool      = [t for t in candidate_tests if t not in suite]

    while remaining:
        useful = [(t, cov_map.get(t, set()) & remaining)
                  for t in pool if cov_map.get(t, set()) & remaining]
        if not useful:
            return None
        max_gain = max(len(g) for _, g in useful)
        best     = [t for t, g in useful if len(g) == max_gain]
        chosen   = rng.choice(best)
        suite.add(chosen)
        remaining -= cov_map.get(chosen, set())
        pool.remove(chosen)

    return suite


def augment_suites(data: CoverageData, initial_suites: list,
                   criterion_b: str, n_augmentations: int, seed: int) -> list:
    """
    Augment each suite toward criterion_b and check fault revelation.
    Preconditions:  initial_suites non-empty, criterion_b exists
    Postconditions: every augmented suite is adequate for criterion_b
    """
    rng       = random.Random(seed)
    all_tests = list(data.all_tests)
    results   = []

    for initial_suite in initial_suites:
        res = {
            'initial_suite': initial_suite,
            'initial_size' : len(initial_suite),
            'augmentations': []
        }
        seen     = []
        attempts = 0

        while len(res['augmentations']) < n_augmentations and attempts < n_augmentations * 50:
            attempts += 1
            shuffled  = list(all_tests)
            rng.shuffle(shuffled)
            augmented = _greedy_augment(data, criterion_b, initial_suite, shuffled, rng)

            if augmented is None:
                continue
            if not is_adequate(data, criterion_b, augmented):
                continue
            if augmented in seen:
                continue

            seen.append(augmented)
            res['augmentations'].append({
                'suite'    : augmented,
                'size'     : len(augmented),
                'added'    : augmented - initial_suite,
                'revealing': is_revealing(data, augmented)
            })

        results.append(res)

    return results