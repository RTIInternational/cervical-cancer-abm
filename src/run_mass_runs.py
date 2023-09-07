import argparse
import os
from pathlib import Path

import experiments.india.src.make_targets as india
import experiments.japan.src.make_targets as japan
import experiments.zambia.src.make_targets as zambia
import experiments.usa.src.make_targets as usa
import pandas as pd
from model.cervical_model import CervicalModel
from model.logger import LoggerFactory

from src.helper_functions import multi_process
from src.mass_run_analysis import analyze_results


def extract_results(experiment_dir: Path):
    # ----- Extract the results
    analysis_values = pd.DataFrame()
    final_selected = pd.DataFrame()
    for item in os.listdir(experiment_dir):
        if "scenario_" in item:
            if not item[-4:].isdigit():
                continue
            if "analysis_values.csv" in os.listdir(experiment_dir.joinpath(item, "iteration_0")):
                # Read analysis values
                results = pd.read_csv(experiment_dir.joinpath(item, "iteration_0", "analysis_values.csv"))
                results = results.rename(columns={"0": item})
                analysis_values[item] = results[item].values
                # Selected Multipliers
                selected = pd.read_csv(experiment_dir.joinpath(item, "selected_multipliers.csv"))
                final_selected[item] = selected.loc[0].values[1:]

    # Analysis Values
    analysis_values.to_csv(experiment_dir.joinpath("analysis_values.csv"), index=True)
    # Output selected multipliers
    final_selected = final_selected.reindex(sorted(final_selected.columns), axis=1)
    final_selected.to_csv(experiment_dir.joinpath("selected_multipliers.csv"), index=False)

    # Analyze Values
    analyze_results(analysis_values, experiment_dir)


def get_run_analysis(scenario_dir):
    if "india" in str(scenario_dir):
        return india.run_analysis
    if "japan" in str(scenario_dir):
        return japan.run_analysis
    if "zambia" in str(scenario_dir):
        return zambia.run_analysis
    if "usa" in str(scenario_dir):
        return usa.run_analysis


def run_and_analyze(scenario_dir, print_status: bool = False, limit_steps: int = None):
    model = CervicalModel(scenario_dir, 0, logger=LoggerFactory().create_logger())
    if limit_steps:
        model.params.num_steps = limit_steps
    model.run(print_status)
    run_analysis = get_run_analysis(scenario_dir)
    run_analysis(scenario_dir, 0)


def main(args):
    experiment_dir = Path(f"experiments/{args.country}")
    logger_factory = LoggerFactory()
    logger = logger_factory.create_logger(experiment_dir.joinpath("mass_runs.log"))
    logger.info("Starting runs.")

    run_list = []
    for scenario in experiment_dir.iterdir():
        if "scenario_" in scenario.name:
            if "iteration_0" not in scenario.iterdir():
                run_list.append({"scenario_dir": scenario})
    multi_process(run_and_analyze, run_list, logger, "scenario_dir")

    extract_results(experiment_dir)


if __name__ == "__main__":
    """ Mass runs are completed so that several parameter sets can be tested.
    The final goal is to review how the run did compared to the country's target values.
    The 'analyze' function is not ran here. This is not a "batch".
    """
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("country", type=str, default="all", help="Name of the country.")
    args = parser.parse_args()

    main(args)
