"""
main.py
Command-line entry point for the coverage analysis tool.

Usage:
    python main.py --labels <path1> <path2> ... --result <path>
                   --criterion-a <name> --criterion-b <name>
                   [--n-suites <int>] [--n-augmentations <int>]
                   [--seed <int>] [--fault-index <int>]
                   [--output-dir <path>]

Example:
    python main.py \
        --labels data/STMT/tcas_Original/tcas_Original.labels \
                 data/ADC/tcas_Original/tcas_Original.labels \
        --result data/Result_tcas.txt \
        --criterion-a STMT \
        --criterion-b ADC \
        --n-suites 10 \
        --n-augmentations 5 \
        --seed 42
"""

import argparse
import sys
import time

import ingestion
import coverage_engine
import suite_generator
import suite_augmentor
import reporter


def parse_args():
    p = argparse.ArgumentParser(description="Coverage-based fault revelation tool.")
    p.add_argument('--labels',          required=True, nargs='+',
                   help='One or more paths to .labels files')
    p.add_argument('--result',          required=True)
    p.add_argument('--criterion-a',     required=True)
    p.add_argument('--criterion-b',     required=True)
    p.add_argument('--n-suites',        type=int, default=100)
    p.add_argument('--n-augmentations', type=int, default=10)
    p.add_argument('--seed',            type=int, default=42)
    p.add_argument('--fault-index',     type=int, default=0)
    p.add_argument('--output-dir',      default='results')
    return p.parse_args()


def main():
    args = parse_args()
    t0   = time.time()

    print(f"[1/5] Loading data...")
    data = ingestion.load_multiple(args.labels, args.result, args.fault_index)
    print(f"      Tests in pool  : {len(data.all_tests)}")
    print(f"      Revealing tests: {len(data.revealing_tests)}")
    coverage_engine.print_coverage_summary(data)

    for crit in (args.criterion_a, args.criterion_b):
        if crit not in data.max_pool_coverage:
            print(f"[ERROR] Criterion '{crit}' not found.", file=sys.stderr)
            print(f"        Available: {list(data.max_pool_coverage.keys())}", file=sys.stderr)
            sys.exit(1)

    print(f"[2/5] Generating {args.n_suites} suites...")
    suites = suite_generator.generate_suites(
        data, args.criterion_a, args.criterion_b,
        args.n_suites, args.seed)
    print(f"      Generated {len(suites)} suites.")

    if not suites:
        print("[ERROR] No qualifying suites generated.", file=sys.stderr)
        sys.exit(1)

    print(f"[3/5] Augmenting suites...")
    results = suite_augmentor.augment_suites(
        data, suites, args.criterion_b,
        args.n_augmentations, args.seed + 1)

    print("[4/5] Computing summary...")
    total_aug = sum(len(r['augmentations']) for r in results)
    total_rev = sum(sum(1 for a in r['augmentations'] if a['revealing']) for r in results)
    pct = 100.0 * total_rev / total_aug if total_aug else 0.0
    print(f"      Augmentations: {total_aug}, Revealed: {total_rev} ({pct:.1f}%)")

    print(f"[5/5] Exporting results to {args.output_dir}/...")
    reporter.export_results(data, results, args.criterion_a,
                            args.criterion_b, args.output_dir)

    print(f"\nDone in {time.time() - t0:.2f}s.")


if __name__ == '__main__':
    main()