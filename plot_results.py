"""
plot_results.py
Reads benchmark_results.csv and generates box plots
for each execution phase.

Install: pip install matplotlib
Usage:   python plot_results.py
"""

import csv
import statistics
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def load_data(filepath: str = 'benchmark_results.csv') -> dict:
    """Load benchmark CSV into a dict of phase -> list of times."""
    data = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key, val in row.items():
                if key not in data:
                    data[key] = []
                data[key].append(float(val))
    return data


def main():
    data = load_data()

    phases = ['ingestion', 'suite_generation', 'augmentation', 'reporting', 'total']
    labels = ['Ingestion', 'Suite\nGeneration', 'Augmentation', 'Reporting', 'Total']
    values = [data[p] for p in phases]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Execution Time Distribution per Phase (seconds)',
                 fontsize=14, fontweight='bold', y=1.01)

    # ── Plot 1: All phases including total ──────────────────────────────────
    ax1 = axes[0]
    bp1 = ax1.boxplot(values,
                      labels=labels,
                      patch_artist=True,
                      medianprops=dict(color='black', linewidth=2),
                      flierprops=dict(marker='o', markerfacecolor='gray',
                                      markersize=4, alpha=0.5))

    colors = ['#5DCAA5', '#378ADD', '#D85A30', '#7F77DD', '#888780']
    for patch, color in zip(bp1['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax1.set_ylabel('Time (seconds)')
    ax1.set_title('All Phases')
    ax1.grid(axis='y', linestyle='--', alpha=0.4)
    ax1.tick_params(axis='x', labelsize=9)

    # ── Plot 2: Individual phases only (excluding total) ────────────────────
    ax2 = axes[1]
    ind_phases = ['ingestion', 'suite_generation', 'augmentation', 'reporting']
    ind_labels = ['Ingestion', 'Suite\nGeneration', 'Augmentation', 'Reporting']
    ind_values = [data[p] for p in ind_phases]

    bp2 = ax2.boxplot(ind_values,
                      labels=ind_labels,
                      patch_artist=True,
                      medianprops=dict(color='black', linewidth=2),
                      flierprops=dict(marker='o', markerfacecolor='gray',
                                      markersize=4, alpha=0.5))

    for patch, color in zip(bp2['boxes'], colors[:4]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax2.set_ylabel('Time (seconds)')
    ax2.set_title('Individual Phases (excl. total)')
    ax2.grid(axis='y', linestyle='--', alpha=0.4)
    ax2.tick_params(axis='x', labelsize=9)

    # ── Summary stats table below plots ─────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"{'Phase':<22} {'N':>4} {'Mean':>8} {'Median':>8} "
          f"{'Std':>8} {'Min':>8} {'Max':>8}")
    print(f"{'-'*65}")
    for phase, label in zip(phases, labels):
        vals = data[phase]
        label_clean = label.replace('\n', ' ')
        print(f"{phase:<22} {len(vals):>4} "
              f"{statistics.mean(vals):>8.4f} "
              f"{statistics.median(vals):>8.4f} "
              f"{statistics.stdev(vals):>8.4f} "
              f"{min(vals):>8.4f} "
              f"{max(vals):>8.4f}")
    print(f"{'='*65}")

    plt.tight_layout()
    plt.savefig('benchmark_boxplots.png', dpi=150, bbox_inches='tight')
    print("\nBox plots saved to benchmark_boxplots.png")
    plt.show()


if __name__ == '__main__':
    main()