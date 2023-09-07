import argparse
from pathlib import Path

import pandas as pd
from model.cervical_model import CervicalModel
from model.logger import LoggerFactory

from src.analyze import analyze
from src.prep_scenario import prepare_scenario
from src.run_mass_runs import get_run_analysis


def run_and_analyze(scenario_dir, print_status: bool = False):
    print(f"Starting model for: {scenario_dir}")
    model = CervicalModel(scenario_dir, 0, logger=LoggerFactory().create_logger())
    model.run(print_status)
    run_analysis = get_run_analysis(scenario_dir)
    run_analysis(scenario_dir, 0)
    analyze(scenario_dir, 0)


def main(args):
    experiment_dir = Path(f"experiments/{args.country}")
    scenario_dir = experiment_dir.joinpath("scenario_base")
    cm_df = pd.read_csv(experiment_dir.joinpath("base_documents/curve_multipliers.csv"))

    # ----- Prepare Model
    prepare_scenario(
        experiment_dir=experiment_dir,
        scenario_dir=scenario_dir,
        cm_df=cm_df,
        use_selected=True,
        test_multipliers=False,
        num_agents=50_000,
    )

    # ----- Run Model
    run_and_analyze(scenario_dir, print_status=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("country", type=str, default="all", help="Name of the country.")
    args = parser.parse_args()
    main(args)
