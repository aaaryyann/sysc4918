"""
models.py
Shared data structures for the coverage analysis tool.
All modules import from here.
"""

from dataclasses import dataclass, field


@dataclass
class CoverageData:
    """
    Central data structure holding all coverage and fault revelation information.

    coverage:           criterion -> test_id -> set of objective ids covered
    obj_to_tests:       criterion -> obj_id  -> set of test_ids that cover it
    max_pool_coverage:  criterion -> set of coverable objective ids (union across all tests)
    uncoverable:        criterion -> set of objective ids marked uncoverable
    revealing_tests:    set of test_ids that reveal the fault
    all_tests:          sorted list of all test ids in the pool
    """
    coverage:           dict = field(default_factory=dict)
    obj_to_tests:       dict = field(default_factory=dict)
    max_pool_coverage:  dict = field(default_factory=dict)
    uncoverable:        dict = field(default_factory=dict)
    revealing_tests:    set  = field(default_factory=set)
    all_tests:          list = field(default_factory=list)