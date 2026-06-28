"""
benchmark.py
Runs the tool N times and records execution times per phase.
Outputs results to benchmark_results.csv for box plot analysis.

Usage:
    python benchmark.py \
        --labels data/STMT/tcas_Original/tcas_Original.labels \
                 data/ADC/tcas_Original/tcas_Original.labels \
        --result data/Result_tcas.txt \
        --criterion-a ADC \
        --criterion-b STMT \
        --n-suites 10 \
        --n-augmentations 5 \
        --runs 35
"""

import argparse
import csv
import time
import statistics

import ingestion
import coverage_engine
import suite_generator
import suite_augmentor
import reporter


def parse_args():
    p = argparse.ArgumentParser(description="Benchmark the coverage tool.")
    p.add_argument('--labels',          required=True, nargs='+')
    p.add_argument('--result',          required=True)
    p.add_argument('--criterion-a',     required=True)
    p.add_argument('--criterion-b',     required=True)
    p.add_argument('--n-suites',        type=int, default=10)
    p.add_argument('--n-augmentations', type=int, default=5)
    p.add_argument('--runs',            type=int, default=35)
    p.add_argument('--output',          default='benchmark_results.csv')
    return p.parse_args()


def run_once(args, seed: int) -> dict:
    """Run one full experiment and return timing for each phase."""
    times = {}

    # Phase 1: Ingestion
    t0 = time.perf_counter()
    data = ingestion.load_multiple(args.labels, args.result, 0)
    times['ingestion'] = time.perf_counter() - t0

    # Phase 2: Suite generation
    t0 = time.perf_counter()
    suites = suite_generator.generate_suites(
        data, args.criterion_a, args.criterion_b,
        args.n_suites, seed)
    times['suite_generation'] = time.perf_counter() - t0

    if not suites:
        return None

    # Phase 3: Augmentation
    t0 = time.perf_counter()
    results = suite_augmentor.augment_suites(
        data, suites, args.criterion_b,
        args.n_augmentations, seed + 1)
    times['augmentation'] = time.perf_counter() - t0

    # Phase 4: Reporting
    t0 = time.perf_counter()
    reporter.export_results(
        data, results,
        args.criterion_a, args.criterion_b,
        output_dir='benchmark_output')
    times['reporting'] = time.perf_counter() - t0

    times['total'] = sum(times.values())
    return times


def main():
    args = parse_args()
    all_times = []

    print(f"Running {args.runs} iterations...")

    for i in range(args.runs):
        seed = 42 + i
        result = run_once(args, seed)
        if result is None:
            print(f"  Run {i+1}: skipped (no suites generated)")
            continue
        all_times.append(result)
        print(f"  Run {i+1}/{args.runs}: total={result['total']:.4f}s  "
              f"ingest={result['ingestion']:.4f}s  "
              f"gen={result['suite_generation']:.4f}s  "
              f"aug={result['augmentation']:.4f}s")

    if not all_times:
        print("No successful runs.")
        return

    # Write CSV
    with open(args.output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_times[0].keys())
        writer.writeheader()
        writer.writerows(all_times)

    # Print summary statistics
    print(f"\n{'='*55}")
    print(f"{'Phase':<22} {'Mean':>8} {'Median':>8} {'Std':>8} {'Min':>8} {'Max':>8}")
    print(f"{'-'*55}")
    for phase in ['ingestion', 'suite_generation', 'augmentation', 'reporting', 'total']:
        vals = [r[phase] for r in all_times]
        print(f"{phase:<22} "
              f"{statistics.mean(vals):>8.4f} "
              f"{statistics.median(vals):>8.4f} "
              f"{statistics.stdev(vals):>8.4f} "
              f"{min(vals):>8.4f} "
              f"{max(vals):>8.4f}")
    print(f"{'='*55}")
    print(f"\nResults written to {args.output}")
    print("Run plot_results.py to generate box plots.")


if __name__ == '__main__':
    main()