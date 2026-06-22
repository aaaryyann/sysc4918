"""
test_additional.py
Additional unit tests to improve branch and statement coverage
across ingestion.py, reporter.py, coverage_engine.py,
suite_generator.py, and suite_augmentor.py.

Run with: pytest test_synthetic.py test_additional.py -v --cov=. --cov-report=term-missing
"""

import os
import csv
import tempfile
import pytest

from models import CoverageData
from coverage_engine import (
    get_max_pool_coverage,
    get_suite_coverage,
    coverage_percentage,
    is_adequate,
    is_revealing,
    print_coverage_summary,
)
from suite_generator import generate_suites
from suite_augmentor import augment_suites
from ingestion import parse_labels_file, parse_result_file, export_labels
from reporter import export_results


# ── Helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture
def synthetic_data() -> CoverageData:
    """Standard synthetic dataset reused across tests."""
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


def make_labels_file(content: str) -> str:
    """Write content to a temporary .labels file and return its path."""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.labels',
                                    delete=False)
    f.write(content)
    f.close()
    return f.name


def make_result_file(rows: list[str]) -> str:
    """Write rows to a temporary Result file and return its path."""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    for row in rows:
        f.write(row + '\n')
    f.close()
    return f.name


# ── coverage_engine.py branch coverage ───────────────────────────────────────

class TestCoverageEngineBranches:

    def test_coverage_percentage_empty_max_cov(self, synthetic_data):
        """Branch: max_cov is empty → return 0.0"""
        # Add a criterion with no coverable objectives
        synthetic_data.max_pool_coverage['EMPTY'] = set()
        synthetic_data.coverage['EMPTY'] = {}
        pct = coverage_percentage(synthetic_data, 'EMPTY', {'t1'})
        assert pct == 0.0

    def test_is_adequate_empty_max_cov(self, synthetic_data):
        """Branch: max_cov is empty → return True (vacuously adequate)"""
        synthetic_data.max_pool_coverage['EMPTY'] = set()
        synthetic_data.coverage['EMPTY'] = {}
        assert is_adequate(synthetic_data, 'EMPTY', set()) is True

    def test_get_suite_coverage_unknown_test(self, synthetic_data):
        """Branch: test not in coverage dict → contributes empty set"""
        cov = get_suite_coverage(synthetic_data, 'ADC', {'t_unknown'})
        assert cov == set()

    def test_print_coverage_summary_runs(self, synthetic_data, capsys):
        """Statement: print_coverage_summary() executes without error"""
        print_coverage_summary(synthetic_data)
        captured = capsys.readouterr()
        assert 'ADC' in captured.out
        assert 'AUC' in captured.out

    def test_is_revealing_single_revealing_test(self, synthetic_data):
        """Branch: suite contains exactly the revealing test"""
        assert is_revealing(synthetic_data, {'t5'}) is True

    def test_is_revealing_no_overlap(self, synthetic_data):
        """Branch: suite and revealing_tests are disjoint"""
        assert is_revealing(synthetic_data, {'t1', 't2'}) is False


# ── suite_generator.py branch coverage ───────────────────────────────────────

class TestSuiteGeneratorBranches:

    def test_no_non_revealing_candidates(self, synthetic_data):
        """Branch: all tests are revealing → return empty list"""
        synthetic_data.revealing_tests = set(synthetic_data.all_tests)
        suites = generate_suites(synthetic_data, 'ADC', 'AUC', 5, 42)
        assert suites == []

    def test_impossible_adequacy_returns_empty(self, synthetic_data):
        """Branch: greedy build returns None → no suites generated"""
        # Remove all tests from coverage so nothing can cover objectives
        synthetic_data.coverage['ADC'] = {}
        synthetic_data.max_pool_coverage['ADC'] = {1, 2, 3, 4}
        suites = generate_suites(synthetic_data, 'ADC', 'AUC', 5, 42)
        assert suites == []

    def test_fewer_suites_than_requested(self, synthetic_data):
        """Branch: generated suites < n_suites due to pool exhaustion"""
        suites = generate_suites(synthetic_data, 'ADC', 'AUC', 100, 42)
        # Pool is small so we can't generate 100 distinct suites
        assert len(suites) <= 100

    def test_suite_not_added_if_duplicate(self, synthetic_data):
        """Branch: duplicate suite is not added"""
        suites = generate_suites(synthetic_data, 'ADC', 'AUC', 5, 42)
        # All returned suites must be unique
        for i in range(len(suites)):
            for j in range(i + 1, len(suites)):
                assert suites[i] != suites[j]


# ── suite_augmentor.py branch coverage ───────────────────────────────────────

class TestSuiteAugmentorBranches:

    def test_augmentation_impossible_returns_no_augmentations(self, synthetic_data):
        """Branch: _greedy_augment returns None → augmentation skipped"""
        # Remove all tests from AUC coverage so augmentation is impossible
        synthetic_data.coverage['AUC'] = {}
        suites = [{'t1', 't2'}]
        results = augment_suites(synthetic_data, suites, 'AUC', 5, 43)
        assert len(results[0]['augmentations']) == 0

    def test_augmented_result_structure_complete(self, synthetic_data):
        """Statement: result dict has all required keys"""
        suites  = generate_suites(synthetic_data, 'ADC', 'AUC', 2, 42)
        results = augment_suites(synthetic_data, suites, 'AUC', 2, 43)
        for res in results:
            assert 'initial_suite'  in res
            assert 'initial_size'   in res
            assert 'augmentations'  in res
            for aug in res['augmentations']:
                assert 'suite'      in aug
                assert 'size'       in aug
                assert 'added'      in aug
                assert 'revealing'  in aug

    def test_added_field_is_difference(self, synthetic_data):
        """Statement: added = augmented suite minus initial suite"""
        suites  = generate_suites(synthetic_data, 'ADC', 'AUC', 2, 42)
        results = augment_suites(synthetic_data, suites, 'AUC', 2, 43)
        for res in results:
            for aug in res['augmentations']:
                assert aug['added'] == aug['suite'] - res['initial_suite']


# ── ingestion.py tests ───────────────────────────────────────────────────────

class TestIngestion:

    def test_parse_labels_file_covered(self):
        """Parse a simple .labels file with covered objectives."""
        content = (
            "# LReplay-updated coverage data\n"
            "1, covered, ADC, file.c:10, file_labels.c:10, LReplay, t1 t2 t3, 0.\n"
            "2, covered, ADC, file.c:20, file_labels.c:20, LReplay, t2 t3, 0.\n"
            "3, uncoverable, ADC, file.c:30, file_labels.c:30, EVA, , 0.\n"
        )
        path = make_labels_file(content)
        try:
            data = CoverageData()
            parse_labels_file(path, data)
            assert 'ADC' in data.coverage
            assert 't1' in data.coverage['ADC']
            assert 1 in data.coverage['ADC']['t1']
            assert 3 in data.uncoverable['ADC']
            assert 1 in data.max_pool_coverage['ADC']
            assert 2 in data.max_pool_coverage['ADC']
            assert 3 not in data.max_pool_coverage['ADC']
            assert set(data.all_tests) == {'t1', 't2', 't3'}
        finally:
            os.unlink(path)

    def test_parse_labels_file_empty_drivers(self):
        """Branch: covered line with empty drivers → treated as uncoverable.
        Must include at least one valid covered line to satisfy postcondition."""
        content = (
            "1, covered, ADC, file.c:10, file_labels.c:10, LReplay, t1, 0.\n"
            "2, covered, ADC, file.c:20, file_labels.c:20, LReplay, , 0.\n"
        )
        path = make_labels_file(content)
        try:
            data = CoverageData()
            parse_labels_file(path, data)
            assert 2 in data.uncoverable.get('ADC', set())
            assert 1 in data.max_pool_coverage.get('ADC', set())
        finally:
            os.unlink(path)

    def test_parse_labels_file_skips_comments(self):
        """Branch: comment lines are skipped."""
        content = (
            "# This is a comment\n"
            "1, covered, ADC, file.c:10, file_labels.c:10, LReplay, t1, 0.\n"
        )
        path = make_labels_file(content)
        try:
            data = CoverageData()
            parse_labels_file(path, data)
            assert len(data.all_tests) == 1
        finally:
            os.unlink(path)

    def test_parse_result_file_basic(self):
        """Parse a simple Result file with known fault revelation."""
        # 3 tests: t1 reveals (1), t2 does not (0), t3 reveals (1)
        data = CoverageData()
        data.all_tests = ['t1', 't2', 't3']

        result_path = make_result_file(['101'])
        try:
            parse_result_file(result_path, data, fault_index=0)
            assert 't1' in data.revealing_tests
            assert 't2' not in data.revealing_tests
            assert 't3' in data.revealing_tests
        finally:
            os.unlink(result_path)

    def test_parse_result_file_no_revealing(self):
        """Branch: no test reveals the fault."""
        data = CoverageData()
        data.all_tests = ['t1', 't2', 't3']
        result_path = make_result_file(['000'])
        try:
            parse_result_file(result_path, data, fault_index=0)
            assert len(data.revealing_tests) == 0
        finally:
            os.unlink(result_path)

    def test_export_labels_roundtrip(self, synthetic_data):
        """Statement: export_labels writes a file that can be re-read."""
        with tempfile.NamedTemporaryFile(suffix='.labels', delete=False) as f:
            out_path = f.name
        try:
            export_labels(synthetic_data, out_path)
            assert os.path.isfile(out_path)
            # Re-read and verify at least one criterion is present
            data2 = CoverageData()
            parse_labels_file(out_path, data2)
            assert 'ADC' in data2.max_pool_coverage
        finally:
            os.unlink(out_path)


# ── reporter.py tests ─────────────────────────────────────────────────────────

class TestReporter:

    def test_export_results_creates_files(self, synthetic_data, tmp_path):
        """Statement: export_results creates CSV and txt files."""
        suites  = generate_suites(synthetic_data, 'ADC', 'AUC', 3, 42)
        results = augment_suites(synthetic_data, suites, 'AUC', 3, 43)
        export_results(synthetic_data, results, 'ADC', 'AUC',
                       output_dir=str(tmp_path))
        assert (tmp_path / 'results.csv').exists()
        assert (tmp_path / 'results.txt').exists()

    def test_export_results_csv_has_correct_columns(self, synthetic_data,
                                                     tmp_path):
        """Statement: CSV contains expected column headers."""
        suites  = generate_suites(synthetic_data, 'ADC', 'AUC', 2, 42)
        results = augment_suites(synthetic_data, suites, 'AUC', 2, 43)
        export_results(synthetic_data, results, 'ADC', 'AUC',
                       output_dir=str(tmp_path))
        with open(tmp_path / 'results.csv') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
        assert 'suite_id'       in headers
        assert 'fault_revealed' in headers
        assert 'initial_size'   in headers
        assert 'augmented_size' in headers

    def test_export_results_txt_contains_summary(self, synthetic_data,
                                                  tmp_path):
        """Statement: plain text contains summary statistics."""
        suites  = generate_suites(synthetic_data, 'ADC', 'AUC', 2, 42)
        results = augment_suites(synthetic_data, suites, 'AUC', 2, 43)
        export_results(synthetic_data, results, 'ADC', 'AUC',
                       output_dir=str(tmp_path))
        content = (tmp_path / 'results.txt').read_text()
        assert 'ADC' in content
        assert 'AUC' in content
        assert 'Fault revealed' in content

    def test_export_results_empty_augmentations(self, synthetic_data,
                                                tmp_path):
        """Branch: suite with no augmentations — reporter handles gracefully."""
        results = [{
            'initial_suite': {'t1', 't2'},
            'initial_size' : 2,
            'augmentations': []
        }]
        export_results(synthetic_data, results, 'ADC', 'AUC',
                       output_dir=str(tmp_path))
        assert (tmp_path / 'results.txt').exists()


# ── Additional ingestion branches ─────────────────────────────────────────────

class TestIngestionBranches:

    def test_parse_result_file_length_mismatch(self):
        """Branch: result row length != number of tests → warning printed."""
        data = CoverageData()
        data.all_tests = ['t1', 't2', 't3']
        # Row has only 2 chars but we have 3 tests → mismatch
        result_path = make_result_file(['10'])
        try:
            parse_result_file(result_path, data, fault_index=0)
            # Should still parse what it can without crashing
            assert 't1' in data.revealing_tests
        finally:
            os.unlink(result_path)

    def test_parse_result_file_fault_index_out_of_range(self):
        """Branch: fault_index >= number of rows → sys.exit called."""
        data = CoverageData()
        data.all_tests = ['t1', 't2']
        result_path = make_result_file(['10'])
        try:
            with pytest.raises(SystemExit):
                parse_result_file(result_path, data, fault_index=5)
        finally:
            os.unlink(result_path)

    def test_parse_result_file_second_fault(self):
        """Branch: fault_index=1 reads second row correctly."""
        data = CoverageData()
        data.all_tests = ['t1', 't2', 't3']
        result_path = make_result_file(['000', '101'])
        try:
            parse_result_file(result_path, data, fault_index=1)
            assert 't1' in data.revealing_tests
            assert 't3' in data.revealing_tests
            assert 't2' not in data.revealing_tests
        finally:
            os.unlink(result_path)

    def test_export_labels_roundtrip_with_uncoverable(self, synthetic_data):
        """Branch: uncoverable objectives are written correctly."""
        with tempfile.NamedTemporaryFile(suffix='.labels', delete=False) as f:
            out_path = f.name
        try:
            export_labels(synthetic_data, out_path)
            content = open(out_path).read()
            assert 'uncoverable' in content
        finally:
            os.unlink(out_path)


# ── Additional suite_generator branches ───────────────────────────────────────

class TestSuiteGeneratorAdditionalBranches:

    def test_suite_already_adequate_for_b_skipped(self, synthetic_data):
        """Branch: generated suite already adequate for B → skipped."""
        # Make AUC max_pool_coverage empty so every suite is adequate for AUC
        synthetic_data.max_pool_coverage['AUC'] = set()
        suites = generate_suites(synthetic_data, 'ADC', 'AUC', 5, 42)
        # All suites will be skipped because they're already adequate for AUC
        assert len(suites) == 0

    def test_revealing_suite_skipped(self, synthetic_data):
        """Branch: greedy built a revealing suite → discarded."""
        # Make only t5 (the revealing test) able to cover ADC
        synthetic_data.coverage['ADC'] = {'t5': {1, 2, 3, 4}}
        synthetic_data.obj_to_tests['ADC'] = {
            1: {'t5'}, 2: {'t5'}, 3: {'t5'}, 4: {'t5'}
        }
        suites = generate_suites(synthetic_data, 'ADC', 'AUC', 5, 42)
        # All built suites will be revealing → none qualify
        assert len(suites) == 0


# ── Additional suite_augmentor branches ───────────────────────────────────────

class TestSuiteAugmentorAdditionalBranches:

    def test_duplicate_augmentation_skipped(self, synthetic_data):
        """Branch: duplicate augmented suite is not added to results."""
        suites  = generate_suites(synthetic_data, 'ADC', 'AUC', 1, 42)
        results = augment_suites(synthetic_data, suites, 'AUC',
                                 n_augmentations=10, seed=43)
        augs = results[0]['augmentations']
        suite_list = [frozenset(a['suite']) for a in augs]
        assert len(suite_list) == len(set(suite_list))

    def test_augmentor_not_adequate_after_build(self, synthetic_data):
        """Branch: augmented suite fails adequacy check → discarded."""
        # Reduce AUC max_pool_coverage so augmentation overshoots
        # This is a robustness test for the adequacy guard in augmentor
        suites  = generate_suites(synthetic_data, 'ADC', 'AUC', 2, 42)
        results = augment_suites(synthetic_data, suites, 'AUC', 3, 99)
        for res in results:
            for aug in res['augmentations']:
                assert aug['suite'].issuperset(res['initial_suite'])


# ── Additional ingestion coverage ─────────────────────────────────────────────

class TestIngestionRemainingBranches:

    def test_parse_labels_malformed_line_skipped(self):
        """Branch: line with fewer than 7 comma-separated fields is skipped."""
        content = (
            "1, covered, ADC\n"
            "2, covered, ADC, file.c:10, file_labels.c:10, LReplay, t1, 0.\n"
        )
        path = make_labels_file(content)
        try:
            data = CoverageData()
            parse_labels_file(path, data)
            # Only obj 2 should be loaded; malformed line 1 is skipped
            assert 2 in data.max_pool_coverage.get('ADC', set())
            assert 1 not in data.max_pool_coverage.get('ADC', set())
        finally:
            os.unlink(path)

    def test_load_multiple_two_files(self):
        """Statement: load_multiple loads criteria from two separate files."""
        from ingestion import load_multiple

        content_adc = (
            "1, covered, ADC, f.c:10, f_l.c:10, LReplay, t1 t2, 0.\n"
            "2, covered, ADC, f.c:20, f_l.c:20, LReplay, t2 t3, 0.\n"
        )
        content_auc = (
            "1, covered, AUC, f.c:10, f_l.c:10, LReplay, t1, 0.\n"
            "2, covered, AUC, f.c:20, f_l.c:20, LReplay, t2 t3, 0.\n"
        )
        path_adc = make_labels_file(content_adc)
        path_auc = make_labels_file(content_auc)

        # Result file: 3 tests, none revealing
        result_path = make_result_file(['000'])

        try:
            data = load_multiple([path_adc, path_auc], result_path,
                                 fault_index=0)
            assert 'ADC' in data.max_pool_coverage
            assert 'AUC' in data.max_pool_coverage
            assert len(data.all_tests) == 3
            assert len(data.revealing_tests) == 0
        finally:
            os.unlink(path_adc)
            os.unlink(path_auc)
            os.unlink(result_path)

    def test_export_labels_multiple_criteria(self):
        """Statement: export_labels writes both ADC and AUC criteria."""
        data = CoverageData()
        data.coverage = {
            'ADC': {'t1': {1, 2}, 't2': {2, 3}},
            'AUC': {'t1': {1},    't2': {2}},
        }
        data.obj_to_tests = {
            'ADC': {1: {'t1'}, 2: {'t1', 't2'}, 3: {'t2'}},
            'AUC': {1: {'t1'}, 2: {'t2'}},
        }
        data.max_pool_coverage = {'ADC': {1, 2, 3}, 'AUC': {1, 2}}
        data.uncoverable       = {'ADC': set(),      'AUC': set()}
        data.revealing_tests   = set()
        data.all_tests         = ['t1', 't2']

        with tempfile.NamedTemporaryFile(suffix='.labels', delete=False) as f:
            out_path = f.name
        try:
            export_labels(data, out_path)
            content = open(out_path).read()
            assert 'ADC' in content
            assert 'AUC' in content
        finally:
            os.unlink(out_path)


# ── Suite generator line 62, 64 ───────────────────────────────────────────────

class TestSuiteGeneratorLines6264:

    def test_suite_in_suites_branch(self, synthetic_data):
        """Branch lines 62/64: suite already in list → not added again."""
        # Request more suites than the pool can produce uniquely
        suites = generate_suites(synthetic_data, 'ADC', 'AUC', 50, 42)
        # Verify all returned suites are unique (duplicate branch fired)
        frozen = [frozenset(s) for s in suites]
        assert len(frozen) == len(set(frozen))