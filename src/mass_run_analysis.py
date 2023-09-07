from pathlib import Path

import pandas as pd


def analyze_results(analysis_values: pd.DataFrame, experiment_dir: Path):
    targets = pd.read_csv(experiment_dir.joinpath("base_documents/targets.csv"))
    expected_array = targets.Value.values
    weights = [targets["Weight"].values[i] / sum(targets.Weight) for i in range(targets.shape[0])]

    # Analysis values:
    av = analysis_values[[i for i in analysis_values.columns if "scen" in i]]

    analysis_output = []
    for column in av.columns:
        array = av[column].values

        # ----- Calculate the Percent difference, and weighted percent difference
        p_diff = abs(array - expected_array) / expected_array
        apd = p_diff.mean()
        weighted_p_diff = p_diff * weights
        weighted_apd = sum(weighted_p_diff)

        # ----- Check that the two main targets work
        # Cause of Cancer
        cause_targets = targets[targets.Category.str.contains("Cause")].index.values
        avg = abs(array - expected_array)[cause_targets].mean()
        cause_cancer_check = False
        if avg < 0.10:
            cause_cancer_check = True

        # Cancer Incidence
        cancer_incidence_targets = targets[targets.Category == "Cancer Incidence"].index.values
        cancer_inc_check = False
        if p_diff[cancer_incidence_targets].mean() < 0.10:
            cancer_inc_check = True
        analysis_output.append([column, apd, weighted_apd, cancer_inc_check, cause_cancer_check])

    analysis_output = pd.DataFrame(analysis_output)
    analysis_output.columns = ["Scenario", "% Diff", "Weighted % Diff", "Incidence Check", "Cause Check"]
    analysis_output.to_csv(experiment_dir.joinpath("analysis_output.csv"), index=False)
