"""
suite_generator.py
Generates non-revealing test suites adequate for criterion A
and NOT adequate for criterion B, using a greedy heuristic.
"""

import random
from models import CoverageData
from coverage_engine import (is_adequate, is_revealing,
                              get_max_pool_coverage, get_suite_coverage)


def _greedy_build_suite(data, criterion, candidate_tests, rng):
    max_cov   = get_max_pool_coverage(data, criterion)
    remaining = set(max_cov)
    suite     = set()
    cov_map   = data.coverage.get(criterion, {})
    pool      = list(candidate_tests)

    while remaining:
        useful = [(t, cov_map.get(t, set()) & remaining)
                  for t in pool if t not in suite
                  and cov_map.get(t, set()) & remaining]
        if not useful:
            return None
        max_gain = max(len(g) for _, g in useful)
        best     = [t for t, g in useful if len(g) == max_gain]
        chosen   = rng.choice(best)
        suite.add(chosen)
        remaining -= cov_map.get(chosen, set())

    return suite


def generate_suites(data: CoverageData, criterion_a: str, criterion_b: str,
                    n_suites: int, seed: int) -> list:
    """
    Generate up to n_suites non-revealing suites adequate for A, not B.
    Preconditions:  both criteria exist, n_suites > 0
    Postconditions: every suite is non-revealing, adequate for A, not adequate for B
    """
    rng        = random.Random(seed)
    candidates = [t for t in data.all_tests if t not in data.revealing_tests]
    if not candidates:
        print("[WARNING] No non-revealing tests available.")
        return []

    max_cov_b    = get_max_pool_coverage(data, criterion_b)
    suites       = []
    attempts     = 0
    max_attempts = n_suites * 50

    while len(suites) < n_suites and attempts < max_attempts:
        attempts += 1
        shuffled = list(candidates)
        rng.shuffle(shuffled)
        suite = _greedy_build_suite(data, criterion_a, shuffled, rng)

        if suite is None:
            continue
        if is_revealing(data, suite):
            continue
        if not is_adequate(data, criterion_a, suite):
            continue
        if max_cov_b.issubset(get_suite_coverage(data, criterion_b, suite)):
            continue
        if suite in suites:
            continue

        suites.append(suite)

    if len(suites) < n_suites:
        print(f"[INFO] Generated {len(suites)}/{n_suites} suites in {attempts} attempts.")

    return suites