import argparse
from pathlib import Path

import pandas as pd


def main(args):
    experiment_dir = Path(f"experiments/{args.country}")

    # Reset HPV and CIN2,3
    for file in ["hpv", "cin23"]:
        df = pd.read_csv(experiment_dir.joinpath(f"base_documents/{file}_curve_multipliers.csv"))
        df["Current"] = 1
        df.to_csv(experiment_dir.joinpath(f"base_documents/{file}_curve_multipliers.csv"), index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a model experiment")
    parser.add_argument("country", type=str, default="all", help="Name of the country.")
    args = parser.parse_args()

    main(args)
