"""
coverage_engine.py
Computes maximum pool coverage and checks test suite adequacy.
Design by Contract enforced via icontract.
"""

import icontract
from models import CoverageData


@icontract.require(lambda data, criterion: criterion in data.max_pool_coverage)
@icontract.ensure(lambda result: isinstance(result, set))
def get_max_pool_coverage(data: CoverageData, criterion: str) -> set:
    """
    Return the set of coverable test objectives for a criterion.
    Preconditions:  criterion exists in data
    Postconditions: returns a set
    """
    return data.max_pool_coverage.get(criterion, set())


@icontract.require(lambda data, criterion: criterion in data.coverage)
@icontract.require(lambda suite: isinstance(suite, set))
@icontract.ensure(lambda result: isinstance(result, set))
def get_suite_coverage(data: CoverageData, criterion: str, suite: set) -> set:
    """
    Return the set of objectives covered by the suite.
    Preconditions:  criterion exists, suite is a set
    Postconditions: returns a set of objective IDs
    """
    covered = set()
    cov = data.coverage.get(criterion, {})
    for t in suite:
        covered |= cov.get(t, set())
    return covered


@icontract.require(lambda data, criterion: criterion in data.max_pool_coverage)
@icontract.require(lambda suite: isinstance(suite, set))
@icontract.ensure(lambda result: 0.0 <= result <= 100.0)
def coverage_percentage(data: CoverageData, criterion: str, suite: set) -> float:
    """
    Return coverage % relative to max pool coverage.
    Preconditions:  criterion exists, suite is a set
    Postconditions: result between 0.0 and 100.0
    """
    max_cov = get_max_pool_coverage(data, criterion)
    if not max_cov:
        return 0.0
    suite_cov = get_suite_coverage(data, criterion, suite)
    return 100.0 * len(suite_cov & max_cov) / len(max_cov)


@icontract.require(lambda data, criterion: criterion in data.max_pool_coverage)
@icontract.require(lambda suite: isinstance(suite, set))
@icontract.ensure(lambda result: isinstance(result, bool))
def is_adequate(data: CoverageData, criterion: str, suite: set) -> bool:
    """
    Return True if suite covers all coverable objectives.
    Preconditions:  criterion exists, suite is a set
    Postconditions: returns bool
    """
    max_cov = get_max_pool_coverage(data, criterion)
    if not max_cov:
        return True
    suite_cov = get_suite_coverage(data, criterion, suite)
    return max_cov.issubset(suite_cov)


@icontract.require(lambda suite: isinstance(suite, set))
@icontract.ensure(lambda result: isinstance(result, bool))
def is_revealing(data: CoverageData, suite: set) -> bool:
    """
    Return True if any test in suite reveals the fault.
    Preconditions:  suite is a set
    Postconditions: returns bool
    """
    return bool(suite & data.revealing_tests)


def print_coverage_summary(data: CoverageData) -> None:
    print("=== Maximum Pool Coverage ===")
    for criterion in sorted(data.max_pool_coverage):
        n_cov   = len(data.max_pool_coverage[criterion])
        n_uncov = len(data.uncoverable.get(criterion, set()))
        print(f"  {criterion}: {n_cov}/{n_cov + n_uncov} coverable "
              f"({n_uncov} uncoverable)")
    print()