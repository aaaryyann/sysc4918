"""
test_synthetic.py
Unit tests using synthetic data.
Run with: pytest test_synthetic.py -v
"""

import pytest
from models import CoverageData
from coverage_engine import (get_max_pool_coverage, get_suite_coverage,
                              coverage_percentage, is_adequate, is_revealing)
from suite_generator import generate_suites
from suite_augmentor import augment_suites


@pytest.fixture
def synthetic_data() -> CoverageData:
    data = CoverageData()
    data.coverage['ADC'] = {
        't1': {1, 2}, 't2': {2, 3}, 't3': {3, 4},
        't4': {1, 4}, 't5': {1, 2, 3, 4}, 't6': {1, 2},
    }
    data.obj_to_tests['ADC'] = {
        1: {'t1','t4','t5','t6'}, 2: {'t1','t2','t5','t6'},
        3: {'t2','t3','t5'},      4: {'t3','t4','t5'},
    }
    data.max_pool_coverage['ADC'] = {1, 2, 3, 4}
    data.uncoverable['ADC']       = {5}

    data.coverage['AUC'] = {
        't1': {1}, 't2': {2}, 't3': {3},
        't4': {1, 2}, 't5': {1, 2, 3}, 't6': {1, 2},
    }
    data.obj_to_tests['AUC'] = {
        1: {'t1','t4','t5','t6'}, 2: {'t2','t4','t5','t6'}, 3: {'t3','t5'},
    }
    data.max_pool_coverage['AUC'] = {1, 2, 3}
    data.uncoverable['AUC']       = set()

    data.revealing_tests = {'t5'}
    data.all_tests       = ['t1', 't2', 't3', 't4', 't5', 't6']
    return data


class TestCoverageDataStructure:
    def test_all_tests_populated(self, synthetic_data):
        assert len(synthetic_data.all_tests) == 6

    def test_revealing_subset_of_all(self, synthetic_data):
        assert synthetic_data.revealing_tests.issubset(set(synthetic_data.all_tests))

    def test_max_pool_adc(self, synthetic_data):
        assert synthetic_data.max_pool_coverage['ADC'] == {1, 2, 3, 4}

    def test_uncoverable_adc(self, synthetic_data):
        assert synthetic_data.uncoverable['ADC'] == {5}


class TestCoverageEngine:
    def test_is_adequate_true(self, synthetic_data):
        assert is_adequate(synthetic_data, 'ADC', {'t1', 't3'}) is True

    def test_is_adequate_false(self, synthetic_data):
        assert is_adequate(synthetic_data, 'ADC', {'t1'}) is False

    def test_coverage_percentage_full(self, synthetic_data):
        assert coverage_percentage(synthetic_data, 'ADC', {'t1', 't3'}) == 100.0

    def test_coverage_percentage_partial(self, synthetic_data):
        assert coverage_percentage(synthetic_data, 'ADC', {'t1'}) == 50.0

    def test_is_revealing_true(self, synthetic_data):
        assert is_revealing(synthetic_data, {'t1', 't5'}) is True

    def test_is_revealing_false(self, synthetic_data):
        assert is_revealing(synthetic_data, {'t1', 't2', 't3'}) is False


class TestSuiteGenerator:
    def test_suites_non_revealing(self, synthetic_data):
        suites = generate_suites(synthetic_data, 'ADC', 'AUC', 5, 42)
        for s in suites:
            assert not is_revealing(synthetic_data, s)

    def test_suites_adequate_for_a(self, synthetic_data):
        suites = generate_suites(synthetic_data, 'ADC', 'AUC', 5, 42)
        for s in suites:
            assert is_adequate(synthetic_data, 'ADC', s)

    def test_suites_not_adequate_for_b(self, synthetic_data):
        suites = generate_suites(synthetic_data, 'ADC', 'AUC', 5, 42)
        for s in suites:
            assert not is_adequate(synthetic_data, 'AUC', s)

    def test_determinism(self, synthetic_data):
        s1 = generate_suites(synthetic_data, 'ADC', 'AUC', 5, 99)
        s2 = generate_suites(synthetic_data, 'ADC', 'AUC', 5, 99)
        assert s1 == s2


class TestSuiteAugmentor:
    def test_augmented_adequate_for_b(self, synthetic_data):
        suites  = generate_suites(synthetic_data, 'ADC', 'AUC', 3, 42)
        results = augment_suites(synthetic_data, suites, 'AUC', 3, 43)
        for res in results:
            for aug in res['augmentations']:
                assert is_adequate(synthetic_data, 'AUC', aug['suite'])

    def test_augmented_contains_initial(self, synthetic_data):
        suites  = generate_suites(synthetic_data, 'ADC', 'AUC', 3, 42)
        results = augment_suites(synthetic_data, suites, 'AUC', 3, 43)
        for res in results:
            for aug in res['augmentations']:
                assert res['initial_suite'].issubset(aug['suite'])

    def test_revealing_field_accurate(self, synthetic_data):
        suites  = generate_suites(synthetic_data, 'ADC', 'AUC', 3, 42)
        results = augment_suites(synthetic_data, suites, 'AUC', 3, 43)
        for res in results:
            for aug in res['augmentations']:
                assert aug['revealing'] == is_revealing(synthetic_data, aug['suite'])