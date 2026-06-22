"""
ingestion.py
Reads and parses all input files into a CoverageData object.
Design by Contract enforced via icontract.

Install: pip install icontract
"""

import os
import re
import sys
import icontract
from models import CoverageData


def _sort_key(test_id: str) -> int:
    m = re.search(r'\d+', test_id)
    return int(m.group()) if m else 0


@icontract.require(lambda filepath: isinstance(filepath, str) and len(filepath) > 0)
@icontract.require(lambda filepath: __import__('os').path.isfile(filepath))
@icontract.require(lambda data: isinstance(data, CoverageData))
@icontract.ensure(lambda data: len(data.all_tests) > 0)
@icontract.ensure(lambda data: len(data.max_pool_coverage) > 0)
def parse_labels_file(filepath: str, data: CoverageData) -> None:
    """
    Parse a .labels file and populate CoverageData.
    Preconditions:  filepath exists, data is CoverageData instance
    Postconditions: data.all_tests non-empty, at least one criterion loaded
    """
    all_test_ids = set()

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split(',', 6)
            if len(parts) < 7:
                continue

            obj_id    = int(parts[0].strip())
            status    = parts[1].strip()
            criterion = parts[2].strip()

            if criterion not in data.coverage:
                data.coverage[criterion]          = {}
                data.obj_to_tests[criterion]      = {}
                data.max_pool_coverage[criterion] = set()
                data.uncoverable[criterion]       = set()

            if status == 'uncoverable':
                data.uncoverable[criterion].add(obj_id)
                continue

            drivers_raw = parts[6].strip()
            drivers_raw = re.sub(r',\s*0\.$', '', drivers_raw).strip()

            if not drivers_raw:
                data.uncoverable[criterion].add(obj_id)
                continue

            test_ids = drivers_raw.split()
            data.obj_to_tests[criterion][obj_id] = set(test_ids)

            for t in test_ids:
                if t not in data.coverage[criterion]:
                    data.coverage[criterion][t] = set()
                data.coverage[criterion][t].add(obj_id)
                all_test_ids.add(t)

            data.max_pool_coverage[criterion].add(obj_id)

    data.all_tests = sorted(all_test_ids, key=_sort_key)


@icontract.require(lambda filepath: isinstance(filepath, str) and len(filepath) > 0)
@icontract.require(lambda filepath: __import__('os').path.isfile(filepath))
@icontract.require(lambda fault_index: fault_index >= 0)
@icontract.require(lambda data: len(data.all_tests) > 0)
def parse_result_file(filepath: str, data: CoverageData,
                      fault_index: int = 0) -> None:
    """
    Parse Result_*.txt fault revelation matrix.
    Preconditions:  filepath exists, fault_index >= 0, all_tests populated
    Postconditions: revealing_tests is subset of all_tests
    """
    with open(filepath, 'r') as f:
        rows = [line.strip() for line in f if line.strip()]

    if fault_index >= len(rows):
        print(f"[ERROR] fault_index {fault_index} out of range.", file=sys.stderr)
        sys.exit(1)

    row = rows[fault_index]
    if len(row) != len(data.all_tests):
        print(f"[WARNING] Row length ({len(row)}) != tests ({len(data.all_tests)}).",
              file=sys.stderr)

    n = min(len(row), len(data.all_tests))
    for i in range(n):
        if row[i] == '1':
            data.revealing_tests.add(data.all_tests[i])

    assert data.revealing_tests.issubset(set(data.all_tests))


@icontract.require(lambda labels_path: __import__('os').path.isfile(labels_path))
@icontract.require(lambda result_path: __import__('os').path.isfile(result_path))
@icontract.require(lambda fault_index: fault_index >= 0)
@icontract.ensure(lambda result: len(result.all_tests) > 0)
def load(labels_path: str, result_path: str, fault_index: int = 0) -> CoverageData:
    """
    Main entry point. Load labels and result files.
    Preconditions:  both files exist, fault_index >= 0
    Postconditions: returned CoverageData has at least one test
    """
    data = CoverageData()
    parse_labels_file(labels_path, data)
    parse_result_file(result_path, data, fault_index)
    return data


@icontract.require(lambda data: len(data.all_tests) > 0)
@icontract.require(lambda output_path: isinstance(output_path, str) and len(output_path) > 0)
def export_labels(data: CoverageData, output_path: str) -> None:
    """
    Write loaded coverage data back to .labels format for verification.
    Preconditions:  data is loaded, output_path is non-empty string
    Postconditions: output file exists
    """
    with open(output_path, 'w') as f:
        f.write("# LReplay-updated coverage data\n")
        f.write("# id, status, tag, origin_loc, current_loc, emitter, drivers, exec_time\n")

        for criterion in sorted(data.max_pool_coverage):
            all_obj_ids = (set(data.obj_to_tests.get(criterion, {}).keys())
                           | data.uncoverable.get(criterion, set()))

            for obj_id in sorted(all_obj_ids):
                if obj_id in data.uncoverable.get(criterion, set()):
                    f.write(f"{obj_id}, uncoverable, {criterion}, "
                            f"unknown, unknown, EVA, , 0.\n")
                else:
                    tests = sorted(data.obj_to_tests[criterion][obj_id], key=_sort_key)
                    drivers = ' '.join(tests)
                    f.write(f"{obj_id}, covered, {criterion}, "
                            f"unknown, unknown, LReplay, {drivers}, 0.\n")

    assert os.path.isfile(output_path)
def load_multiple(labels_paths: list, result_path: str,
                  fault_index: int = 0) -> CoverageData:
    """
    Load multiple .labels files and one Result file into a single CoverageData.
    Each labels file can contain different criteria.
    """
    data = CoverageData()
    for path in labels_paths:
        parse_labels_file(path, data)
    parse_result_file(result_path, data, fault_index)
    return data