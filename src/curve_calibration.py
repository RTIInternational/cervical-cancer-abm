import argparse
from pathlib import Path

import pandas as pd
from model.logger import LoggerFactory

from src.helper_functions import multi_process, read_cm
from src.prep_scenario import prepare_scenario
from src.run_mass_runs import run_and_analyze


def main(args):
    """ Run the curve calibration for a specific country.
    """

    experiment_dir = Path(f"experiments/{args.country}")

    # ----- Setup the Logger
    logger_factory = LoggerFactory()
    logger = logger_factory.create_logger(experiment_dir.joinpath("curve_calibration.log"))

    # ----- Read the base files
    base_dir = experiment_dir.joinpath("base_documents")
    cm = read_cm(experiment_dir)
    analysis_file = "iteration_0/analysis_values.csv"

    num_agents = 100_000
    values = [0.01, 0.05, 0.1, 0.25, 0.4, 0.6, 0.8, 1, 1.33, 1.67, 2, 2.5, 3, 3.5, 4, 4.5, 5, 7.5, 10, 12.5]

    # ----- Start the Calibration --------------------------------------------------------------------------------------
    cm = cm.set_index("Target_Row", drop=False)
    for round_i in range(0, cm.Round.max() + 1):
        print(round_i)
        logger.info(f"Starting round: {round_i}")

        # --- Set the multiplier to be the current value
        rows = cm[cm.Round == round_i]
        cm_dict = dict()
        for scenario_run in range(len(values)):
            cm_dict[scenario_run] = cm.copy()
            cm_dict[scenario_run].loc[rows.index, "Current"] = values[scenario_run]

        # ----- Step #1: Generate the runs -----------------------------------------------------------------------------
        run_list = []
        for scenario_i, item in cm_dict.items():
            run_list.append(
                {
                    "experiment_dir": experiment_dir,
                    "scenario_dir": experiment_dir.joinpath("scenario_{:04}".format(scenario_i)),
                    "cm_df": item,
                    "use_selected": True,
                    "test_multipliers": False,
                    "seed": 1111,
                    "num_agents": num_agents,
                }
            )
        multi_process(prepare_scenario, run_list, logger, "scenario_dir")
        logger.info(f"Runs have been generated for round {round_i}.")

        # ----- Step #2: Run the scenarios -----------------------------------------------------------------------------
        run_list = []
        # Only run for enough steps to capture current age group
        if any(rows.Age.str.contains("\+")):
            step_limit = None
        else:
            step_limit = (int(rows.Age.str[-2:].max()) - 9) * 12 + 12

        for scenario_i, _ in enumerate(cm_dict.items()):
            run_list.append(
                {
                    "scenario_dir": experiment_dir.joinpath("scenario_{:04}".format(scenario_i)),
                    "limit_steps": step_limit,
                }
            )
        multi_process(run_and_analyze, run_list, logger, "scenario_dir")
        logger.info(f"Runs are complete for round {round_i}.")

        # ----- Step #3: Agregate the results --------------------------------------------------------------------------
        results_df = pd.DataFrame()
        for scenario_i, item in enumerate(cm_dict.items()):
            df = pd.read_csv(experiment_dir.joinpath("scenario_{:04}".format(scenario_i), analysis_file))["0"]
            results_df = pd.concat([results_df, df], axis=1)
        results_df.columns = [i for i in range(len(cm_dict))]
        results_df = results_df.loc[cm.Target_Row.values]

        # --- Model the results & predict the best performing multiplier
        for _, row in rows.iterrows():
            row_id = row.Target_Row
            model_df = pd.DataFrame(results_df.loc[row_id])
            model_df.columns = ["modeled_values"]
            model_df["multipliers"] = values

            target = row.Target

            try:
                mv = model_df.modeled_values
                low_index = model_df.loc[(mv < target) & (mv.shift(-1) > target)].index[0]
                low = mv.loc[low_index]
                high = mv.loc[low_index + 1]
                diff1 = high - low
                diff2 = target - low
                ratio = diff2 / diff1
                low_multiplier = model_df.loc[low_index].multipliers
                high_multiplier = model_df.loc[low_index + 1].multipliers
                best_multiplier = (high_multiplier - low_multiplier) * ratio + low_multiplier
            except Exception as E:
                E
                location = mv[min(abs(mv - target)) == abs(mv - target)]
                best_multiplier = model_df.multipliers.values[location.index[0]]
            # Update the final curve multiplier dataframe
            cm.loc[row_id, "Current"] = best_multiplier

        # ----- Step #5: Save after each iteration just in case an error occurs.
        cm.to_csv(base_dir.joinpath("curve_multipliers.csv"), index=False)
    logger.info("Calibration Complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a model experiment")
    parser.add_argument("country", type=str, default="all", help="Name of the country.")
    main(parser.parse_args())
