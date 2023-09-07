import argparse
from pathlib import Path

import pandas as pd

from src.prep_scenario import (
    create_list_of_updates,
    create_multipliers,
    save_cancer,
    update_and_save_hiv,
    update_and_save_hpv,
    update_and_save_life,
)

from src.helper_functions import multi_process
from model.logger import LoggerFactory


def main(country: str):
    # ----- Setup directories
    experiment_dir = Path(f"experiments/{country}")
    result_dir = experiment_dir.joinpath("base_documents/calibration/first_pass/")
    baseline_dir = experiment_dir.joinpath("transition_dictionaries")
    transition_directory = Path(experiment_dir, "transition_pickles")

    # ----- Read all required files
    # Selected multipleirs created from calibration
    selected_multipliers = pd.read_csv(result_dir.joinpath("selected_multipliers.csv"))
    # Base multipliers file
    multiplier_df = pd.read_csv(experiment_dir.joinpath("base_documents/multipliers.csv"))
    # Curve multipliers file
    cm_df = pd.read_csv(experiment_dir.joinpath("base_documents/curve_multipliers.csv"))

    # ----- Find the best 50 performing parameter sets:
    analysis_output = pd.read_csv(result_dir.joinpath("analysis_output.csv"))
    analysis_output.sort_values(by=["Weighted % Diff"], inplace=True)
    analysis_output.sort_values(by=["Cause Check", "Weighted % Diff"], ascending=[False, True], inplace=True)
    analysis_output.reset_index(drop=True, inplace=True)

    # Create 50 different transition probability sets
    for i in range(0, 50):
        print("Preparing parameter set {}".format(i))
        scenario = analysis_output.Scenario.values[i]
        temp_dir = Path(transition_directory, str(i))
        temp_dir.joinpath("transition_dictionaries").mkdir(exist_ok=True, parents=True)

        # Cancer, Life, HIV
        save_cancer(baseline_dir, temp_dir)
        update_and_save_life(baseline_dir, temp_dir)
        update_and_save_hiv(baseline_dir, temp_dir)

        # HPV
        multiplier_df["Selected"] = selected_multipliers[scenario]
        multipliers = create_multipliers(df=multiplier_df, use_selected=True)
        base_updates = create_list_of_updates(df=multiplier_df, multipliers=multipliers)
        pd.DataFrame(multipliers).transpose().to_csv(temp_dir.joinpath("selected_multipliers.csv"), index=False)
        update_and_save_hpv(baseline_dir, temp_dir, base_updates, cm_df)


if __name__ == "__main__":
    """Create different sets of transition probabilities to use for each scenario.
    """
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--country", type=str, default="all", help="Directory for the experiment.")

    args = parser.parse_args()
    if args.country == "all":
        run_list = []
        for country in ["zambia", "japan", "usa", "india"]:
            run_list.append({"country": country})
        multi_process(main, run_list, LoggerFactory().create_logger(), "country")
    else:
        main(args.country)
