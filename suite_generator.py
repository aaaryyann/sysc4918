"""
suite_generator.py
Generates non-revealing test suites adequate for criterion A
and NOT adequate for criterion B, using a greedy heuristic.
"""

import random
import icontract
from models import CoverageData
from coverage_engine import (is_adequate, is_revealing,
                              get_max_pool_coverage, get_suite_coverage)


def _greedy_build_suite(data: CoverageData,
                        criterion: str,
                        candidate_tests: list,
                        rng: random.Random) -> object:
    """
    Build an approximately minimal test suite adequate for criterion
    using a greedy set-cover heuristic on candidate_tests.

    At each step, pick the test that covers the most uncovered objectives.
    Ties are broken randomly for diversity.

    Returns the suite as a set of test IDs, or None if adequacy is
    impossible with the given candidates.

    Greedy heuristic principle:
        At each iteration, select the test case from the candidate pool
        that covers the greatest number of still-uncovered test objectives
        (maximum marginal gain). Ties are broken by random selection to
        introduce diversity across runs. This is a standard greedy
        approximation for the minimum set cover problem, which guarantees
        a solution of size at most O(log n) times the optimal minimum,
        where n is the number of objectives to cover.
    """
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

        max_gain = max(len(gain) for _, gain in useful)
        best     = [t for t, gain in useful if len(gain) == max_gain]
        chosen   = rng.choice(best)
        suite.add(chosen)
        remaining -= cov_map.get(chosen, set())

    return suite


@icontract.require(lambda data, criterion_a: criterion_a in data.max_pool_coverage,
                   description="criterion_a must exist in data")
@icontract.require(lambda data, criterion_b: criterion_b in data.max_pool_coverage,
                   description="criterion_b must exist in data")
@icontract.require(lambda n_suites: n_suites > 0,
                   description="n_suites must be positive")
@icontract.ensure(
    lambda result: len(result) == len(set(frozenset(s) for s in result)),
    description="all returned suites must be unique")
@icontract.ensure(
    lambda result: len(result) >= 0,
    description="result is a list of zero or more suites")
def generate_suites(data: CoverageData,
                    criterion_a: str,
                    criterion_b: str,
                    n_suites: int,
                    seed: int) -> list:
    """
    Generate up to n_suites non-revealing test suites that are:
        - adequate for criterion_a
        - NOT adequate for criterion_b
        - non-revealing
        - approximately minimal (greedy heuristic)
        - all mutually distinct (no two suites contain the same set of tests)

    If fewer than n_suites qualifying unique suites can be constructed
    from the pool (due to pool size or structure), the function returns
    as many as possible and prints an informational message.

    Preconditions:
        - criterion_a and criterion_b exist in data
        - n_suites > 0

    Postconditions:
        - every suite S in result satisfies is_adequate(data, criterion_a, S)
        - every suite S in result satisfies NOT is_adequate(data, criterion_b, S)
        - every suite S in result satisfies NOT is_revealing(data, S)
        - all suites in result are mutually distinct
        - len(result) <= n_suites
    """
    rng = random.Random(seed)

    candidates = [t for t in data.all_tests
                  if t not in data.revealing_tests]

    if not candidates:
        print("[WARNING] No non-revealing tests available in pool.")
        return []

    max_cov_b = get_max_pool_coverage(data, criterion_b)
    suites    = []
    attempts  = 0
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
        print(f"[INFO] Generated {len(suites)}/{n_suites} requested suites "
              f"after {attempts} attempts. The pool may not contain enough "
              f"distinct qualifying subsets.")

    return suites