"""
reporter.py
Exports experimental results as CSV and plain text.
"""

import csv
import os
from models import CoverageData
from coverage_engine import coverage_percentage


def export_results(data: CoverageData, augmentation_results: list,
                   criterion_a: str, criterion_b: str,
                   output_dir: str = ".") -> None:
    """
    Export CSV and plain text summary of results.
    Preconditions:  augmentation_results non-empty, output_dir is a string
    Postconditions: both output files exist after the call
    """
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "results.csv")
    txt_path = os.path.join(output_dir, "results.txt")

    rows            = []
    total_aug       = 0
    total_revealing = 0

    for i, res in enumerate(augmentation_results):
        init    = res['initial_suite']
        i_cov_a = coverage_percentage(data, criterion_a, init)
        i_cov_b = coverage_percentage(data, criterion_b, init)

        for j, aug in enumerate(res['augmentations']):
            a_cov_b = coverage_percentage(data, criterion_b, aug['suite'])
            rows.append({
                'suite_id'                         : i + 1,
                'aug_id'                           : j + 1,
                'initial_size'                     : res['initial_size'],
                'augmented_size'                   : aug['size'],
                'n_tests_added'                    : len(aug['added']),
                f'cov_{criterion_a}_initial_%'     : round(i_cov_a, 2),
                f'cov_{criterion_b}_initial_%'     : round(i_cov_b, 2),
                f'cov_{criterion_b}_augmented_%'   : round(a_cov_b, 2),
                'fault_revealed'                   : aug['revealing']
            })
            total_aug += 1
            if aug['revealing']:
                total_revealing += 1

    if rows:
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    pct = 100.0 * total_revealing / total_aug if total_aug else 0.0

    with open(txt_path, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("EXPERIMENTAL RESULTS SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Criterion A (initial)   : {criterion_a}\n")
        f.write(f"Criterion B (augmented) : {criterion_b}\n\n")
        f.write(f"Suites generated        : {len(augmentation_results)}\n")
        f.write(f"Total augmentations     : {total_aug}\n")
        f.write(f"Fault revealed          : {total_revealing} ({pct:.1f}%)\n")
        f.write(f"Not revealed            : {total_aug - total_revealing}\n\n")
        f.write("-" * 60 + "\n")
        for i, res in enumerate(augmentation_results):
            n_rev  = sum(1 for a in res['augmentations'] if a['revealing'])
            sizes  = [a['size'] for a in res['augmentations']]
            avg_sz = sum(sizes) / len(sizes) if sizes else 0
            f.write(f"  Suite {i+1}: initial={res['initial_size']}, "
                    f"augmentations={len(res['augmentations'])}, "
                    f"revealed={n_rev}, avg_aug_size={avg_sz:.1f}\n")

    print(f"[INFO] Results written to {csv_path} and {txt_path}")