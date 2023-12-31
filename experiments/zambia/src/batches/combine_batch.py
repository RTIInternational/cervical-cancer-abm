import argparse
import csv
from itertools import chain
import pandas as pd
from pathlib import Path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create all input files for a batch of scenarios")
    parser.add_argument("batch", help="name of the batch directory ")
    args = parser.parse_args()

    batch_dir = Path("experiments/zambia").joinpath(args.batch)
    # Collect all the individual results files into a single data structure.
    results = []
    for scenario_dir in batch_dir.glob("scenario_*"):
        for results_file in scenario_dir.glob("**/results.csv"):
            with results_file.open() as f:
                reader = csv.DictReader(f)
                result = next(reader)
                result["scenario"] = scenario_dir.name[len("scenario_") :]
                results.append(result)

    # Compute descriptive stats by scenario.
    results_df = pd.DataFrame(results).set_index("scenario").astype(float)
    groups = results_df.groupby(level=0)

    means = groups.mean()
    stds = groups.std().add_prefix("std_")
    mins = groups.min().add_prefix("min_")
    maxes = groups.max().add_prefix("max_")

    # Combine all the stats, grouping them by variable.
    combined = pd.concat([means, stds, mins, maxes], axis=1)
    column_order = list(chain(*zip(means.columns, stds.columns, mins.columns, maxes.columns)))
    combined = combined[column_order]

    # Export
    combined.to_csv(batch_dir.joinpath("combined_results.csv"))
