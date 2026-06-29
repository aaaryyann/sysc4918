"""
suite_augmentor.py
Augments a non-revealing suite adequate for criterion A
to also satisfy criterion B, then checks for fault revelation.
"""

import random
import icontract
from models import CoverageData
from coverage_engine import (is_adequate, is_revealing,
                              get_max_pool_coverage, get_suite_coverage)


def _greedy_augment(data: CoverageData,
                    criterion_b: str,
                    initial_suite: set,
                    candidate_tests: list,
                    rng: random.Random) -> object:
    """
    Greedily augment initial_suite with tests from candidate_tests
    until it is adequate for criterion_b.

    Augmentation heuristic principle:
        Starting from the initial suite, compute which test objectives
        for criterion_b remain uncovered. At each step, select the test
        from the candidate pool that covers the greatest number of still-
        uncovered objectives (maximum marginal gain). Ties are broken by
        random selection to produce diverse augmentations across runs.
        This continues until all coverable objectives for criterion_b are
        covered, or until no candidate can contribute further coverage
        (in which case None is returned).

    Returns the augmented suite, or None if augmentation is impossible.
    """
    max_cov_b = get_max_pool_coverage(data, criterion_b)
    cov_map   = data.coverage.get(criterion_b, {})

    suite     = set(initial_suite)
    covered   = get_suite_coverage(data, criterion_b, suite)
    remaining = max_cov_b - covered
    pool      = [t for t in candidate_tests if t not in suite]

    while remaining:
        useful = [(t, cov_map.get(t, set()) & remaining)
                  for t in pool
                  if cov_map.get(t, set()) & remaining]

        if not useful:
            return None

        max_gain = max(len(g) for _, g in useful)
        best     = [t for t, g in useful if len(g) == max_gain]
        chosen   = rng.choice(best)

        suite.add(chosen)
        remaining -= cov_map.get(chosen, set())
        pool.remove(chosen)

    return suite


@icontract.require(lambda initial_suites: len(initial_suites) > 0,
                   description="initial_suites must be non-empty")
@icontract.require(lambda data, criterion_b: criterion_b in data.max_pool_coverage,
                   description="criterion_b must exist in data")
@icontract.require(lambda n_augmentations: n_augmentations > 0,
                   description="n_augmentations must be positive")
@icontract.ensure(
    lambda result: all(
        len(r['augmentations']) == len(
            set(frozenset(a['suite']) for a in r['augmentations']))
        for r in result),
    description="augmented suites per initial suite must all be unique")
def augment_suites(data: CoverageData,
                   initial_suites: list,
                   criterion_b: str,
                   n_augmentations: int,
                   seed: int) -> list:
    """
    For each suite in initial_suites, generate up to n_augmentations
    alternative augmentations adequate for criterion_b.

    If fewer than n_augmentations distinct augmented suites can be
    constructed (due to pool size or structure), the function returns
    as many as possible for that suite.

    Preconditions:
        - initial_suites is non-empty
        - criterion_b exists in data
        - n_augmentations > 0

    Postconditions:
        - every augmented suite A satisfies is_adequate(data, criterion_b, A)
        - every augmented suite A is a superset of its initial suite
        - all augmented suites per initial suite are mutually distinct
        - len(augmentations) <= n_augmentations for each suite
    """
    rng       = random.Random(seed)
    all_tests = list(data.all_tests)
    results   = []

    for initial_suite in initial_suites:
        suite_results = {
            'initial_suite': initial_suite,
            'initial_size' : len(initial_suite),
            'augmentations': []
        }

        seen_augmented = []
        attempts       = 0
        max_attempts   = n_augmentations * 50

        while (len(suite_results['augmentations']) < n_augmentations
               and attempts < max_attempts):
            attempts += 1

            shuffled  = list(all_tests)
            rng.shuffle(shuffled)

            augmented = _greedy_augment(
                data, criterion_b, initial_suite, shuffled, rng)

            if augmented is None:
                continue
            if not is_adequate(data, criterion_b, augmented):
                continue
            if augmented in seen_augmented:
                continue

            seen_augmented.append(augmented)
            added     = augmented - initial_suite
            revealing = is_revealing(data, augmented)

            suite_results['augmentations'].append({
                'suite'    : augmented,
                'size'     : len(augmented),
                'added'    : added,
                'revealing': revealing
            })

        results.append(suite_results)

    return results