import argparse
import pickle
from copy import copy
from distutils.dir_util import copy_tree
from pathlib import Path
from shutil import copyfile

import numpy as np
import pandas as pd
from model.state import AgeGroup, CancerDetectionState, CancerState, HivState, HpvImmunity, HpvState, HpvStrain


def to_monthly_prob(val: float, per: int = 1000) -> float:
    return val / (12 * per)


def extrapolate_flat(df: pd.DataFrame, end: int = 75) -> pd.DataFrame:
    df_9 = df.loc[10:10]
    df_9.index = [9]
    df_end = df.loc[end:end]
    df_end_plus = pd.concat([df_end] * (100 - end))
    df_end_plus.index = range(end + 1, 101)

    return pd.concat([df_9, df, df_end_plus])


def make_baseline(df: pd.DataFrame, per: int = 1000, end: int = 75) -> pd.DataFrame:
    return df.set_index("age").apply(to_monthly_prob, per=per).pipe(extrapolate_flat, end=end)


def main(args):
    experiment_dir = Path(f"experiments/{args.country}")
    is_zambia = True if "zambia" in str(experiment_dir) else False
    base_documents_dir = experiment_dir.joinpath("base_documents")
    transition_dictionary_dir = experiment_dir.joinpath("transition_dictionaries")
    transition_dictionary_dir.mkdir(exist_ok=True)
    gh_params_dir = Path("gh_parameters")
    survival = pd.read_csv(base_documents_dir.joinpath("five_year_survival.csv"))
    cin23_cancer = pd.read_csv("experiments/data/cin23_cancer.csv").set_index("Country").loc[experiment_dir.name]

    # ------------------------------------------------------------------------------------------------------------------
    # ----- Life matrix: Monthly probability of dying from all causes
    file = base_documents_dir.joinpath("data/mortality.csv")
    if is_zambia:
        baseline = make_baseline(pd.read_csv(file)[["age", "no_hiv", "hiv"]], per=100_000, end=50)
        # Fit a rough exponential model for extrapolating beyond age 75. Instead of fitting a true model, we'll just
        # estimate the slope on the log scale and extend that out. Prior inspection of the data reveals that this
        # method should produce an adequate extrapolation.
        log_intervals = np.log(baseline).diff().loc[30:50]
        slope = log_intervals.sum()[0] / len(log_intervals)
        for age in range(51, 101):
            baseline.loc[age, "no_hiv"] = np.exp(np.log(baseline.loc[50, "no_hiv"]) + (age - 50) * slope)
            baseline.loc[age, "hiv"] = np.exp(np.log(baseline.loc[50, "hiv"]) + (age - 50) * slope)
    else:
        baseline = make_baseline(pd.read_csv(file)[["age", "no_hiv", "hiv"]], per=10_000)
        mortality = pd.read_csv(base_documents_dir.joinpath("data/mortality.csv"))[["age", "no_hiv", "hiv"]]
        mortality = mortality[(mortality.age >= 9) & (mortality.age <= 100)]
        baseline = mortality.set_index("age").apply(to_monthly_prob, per=10_000)
    baseline.columns = [HivState.NORMAL.name, HivState.HIV.name]

    life_dict = dict()
    for age in baseline.index:
        a = AgeGroup["AGE_{}".format(age)]
        for hiv in HivState:
            # We will use 5-year survival rates for the probabilities or dying for woman who have cancer
            for cancer in CancerState:
                p = baseline.at[age, hiv.name]
                if cancer.value == CancerState.LOCAL:
                    p = 1 - survival[survival.Type == "Local"].Value.values[0] ** (1 / float(60))
                if cancer.value == CancerState.REGIONAL:
                    p = 1 - survival[survival.Type == "Regional"].Value.values[0] ** (1 / float(60))
                if cancer.value == CancerState.DISTANT:
                    p = 1 - survival[survival.Type == "Distant"].Value.values[0] ** (1 / float(60))
                if cancer.value == CancerState.DEAD:  # 0: Can't die if you are already dead
                    p = 0
                life_dict[(a.value, hiv.value, cancer.value)] = p

    # ------------------------------------------------------------------------------------------------------------------
    # ----- HPV matrix
    baseline_normal_to_hpv = make_baseline(pd.read_csv(gh_params_dir.joinpath("normal_to_hpv.csv")))
    baseline_hpv_to_cin1 = make_baseline(pd.read_csv(gh_params_dir.joinpath("hpv_to_cin1.csv")))
    baseline_hpv_cin1_to_cin23 = make_baseline(pd.read_csv(gh_params_dir.joinpath("hpv_cin1_to_cin23.csv")))
    baseline_cin23_to_cancer = make_baseline(pd.read_csv(gh_params_dir.joinpath("cin23_to_cancer.csv")))
    baseline_cin23_regression = make_baseline(pd.read_csv(gh_params_dir.joinpath("cin23_to_normal.csv")))

    # Values for Sixteen and Eighteen were not in Goldhaber paper. Set them equal to high risk values
    baseline_hpv_to_cin1["sixteen"] = baseline_hpv_to_cin1["high_risk"]
    baseline_hpv_to_cin1["eighteen"] = baseline_hpv_to_cin1["high_risk"]
    baseline_hpv_cin1_to_cin23["sixteen"] = baseline_hpv_cin1_to_cin23["high_risk"]
    baseline_hpv_cin1_to_cin23["eighteen"] = baseline_hpv_cin1_to_cin23["high_risk"]

    # --- We are making an effort to get cancer incidence more inline with the strain that causes it: HR, 16, or 18
    hr_ratio = cin23_cancer.Cancer_HR / cin23_cancer.Average_CIN23_HR
    sixteen_ratio = cin23_cancer.Cancer_16 / cin23_cancer.Average_CIN23_16
    eighteen_ratio = cin23_cancer.Cancer_18 / cin23_cancer.Average_CIN23_18
    baseline_cin23_to_cancer["high_risk"] = baseline_cin23_to_cancer["high_risk"]
    baseline_cin23_to_cancer["sixteen"] = baseline_cin23_to_cancer["high_risk"] * sixteen_ratio / hr_ratio
    baseline_cin23_to_cancer["eighteen"] = baseline_cin23_to_cancer["high_risk"] * eighteen_ratio / hr_ratio
    baseline_cin23_to_cancer["low_risk"] = 0

    # Regression based on HPV type was not in Goldhaber paper.
    baseline_cin23_regression["sixteen"] = baseline_cin23_regression["normal"]
    baseline_cin23_regression["eighteen"] = baseline_cin23_regression["normal"]
    baseline_cin23_regression["high_risk"] = baseline_cin23_regression["normal"]
    baseline_cin23_regression["low_risk"] = baseline_cin23_regression["normal"]
    del baseline_cin23_regression["normal"]

    # The text notes that for CIN2,3 regression, 70% clear to Normal, 15% clear to HPV, and 15% clear to CIN1.
    baseline_cin23_to_normal = 0.7 * baseline_cin23_regression
    baseline_cin23_to_hpv = 0.15 * baseline_cin23_regression
    baseline_cin23_to_cin1 = 0.15 * baseline_cin23_regression

    # For regression from CIN1, the text makes no reference to some percentage clearing to HPV.
    # However, the Kim paper says that 70% clear to Normal and 30% clear to HPV, we will use those percentages.
    baseline_cin1_to_normal = 0.7 * to_monthly_prob(371.7)
    baseline_cin1_to_hpv = 0.3 * to_monthly_prob(371.7)

    # Because the rate of regression from HPV and CIN1 is constant across age, we didn't extract its value from the
    # chart image. Instead, we looked it up in Table 2 of the paper and record it here as 371.7 per 1,000 woman-years.
    baseline_hpv_to_normal = to_monthly_prob(371.7)

    hpv_dict = dict()
    for age in baseline.index:
        a = AgeGroup["AGE_{}".format(age)]
        for hpv_strain in HpvStrain:
            # Normal to HPV
            p1 = baseline_normal_to_hpv.at[age, str(hpv_strain)]
            p2 = baseline_hpv_to_cin1.at[age, str(hpv_strain)]
            p3 = baseline_hpv_cin1_to_cin23.at[age, str(hpv_strain)]
            p4 = baseline_hpv_to_normal
            p5 = baseline_hpv_cin1_to_cin23.at[age, str(hpv_strain)]
            p6 = baseline_cin1_to_hpv
            p7 = baseline_cin1_to_normal
            p8 = baseline_cin23_to_cancer.at[age, str(hpv_strain)]
            p9 = baseline_cin23_to_cin1.at[age, str(hpv_strain)]
            p10 = baseline_cin23_to_hpv.at[age, str(hpv_strain)]
            p11 = baseline_cin23_to_normal.at[age, str(hpv_strain)]

            for hpv_imm in HpvImmunity:
                for hpv_state in HpvState:
                    if hpv_state == HpvState.NORMAL:
                        p_values = [1 - p1, p1, 0, 0, 0]
                    elif hpv_state == HpvState.HPV:
                        p_values = [p4, 1 - p4 - p2 - p3, p2, p3, 0]
                    elif hpv_state == HpvState.CIN_1:
                        p_values = [p7, p6, 1 - p7 - p6 - p5, p5, 0]
                    elif hpv_state == HpvState.CIN_2_3:
                        p_values = [p11, p10, p9, 1 - p11 - p10 - p9 - p8, p8]
                    elif hpv_state == HpvState.CANCER:
                        p_values = [0, 0, 0, 0, 1]

                    for hiv_status in HivState:
                        key = (a.value, hpv_strain.value, hpv_imm.value, hpv_state.value, hiv_status.value)
                        hpv_dict[key] = copy(p_values)

    # ------------------------------------------------------------------------------------------------------------------
    # ----- HIV matrix: Only Zambia has HIV probabilities
    if is_zambia:
        baseline_normal_to_hiv = make_baseline(pd.read_csv(base_documents_dir.joinpath("data/normal_to_hiv.csv")))
        hiv_dict = {(k,): baseline_normal_to_hiv.at[k, "hiv"] for k in baseline.index}
    else:
        hiv_dict = {(k,): 0 for k in baseline.index}

    # ------------------------------------------------------------------------------------------------------------------
    # ----- Cancer matrix
    cancer_dict = dict()
    # local to regional: The rates of cancer progression are taken from Table 2 of paper.
    p1 = to_monthly_prob(242.3)
    # regional to distant: The rates of cancer progression are taken from Table 2 of paper.
    p2 = to_monthly_prob(303.8)

    # --- Only Local to Regional and Regional to Distant are allowed.
    # --- We don't model cancer incidence here. Additional events will trigger a transition out of the NORMAL state.
    cancer_dict[(CancerDetectionState.UNDETECTED.value, CancerState.NORMAL.value)] = [1, 0, 0, 0, 0]
    cancer_dict[(CancerDetectionState.UNDETECTED.value, CancerState.LOCAL.value)] = [0, 1 - p1, p1, 0, 0]
    cancer_dict[(CancerDetectionState.UNDETECTED.value, CancerState.REGIONAL.value)] = [0, 0, 1 - p2, p2, 0]
    cancer_dict[(CancerDetectionState.UNDETECTED.value, CancerState.DISTANT.value)] = [0, 0, 0, 1, 0]
    cancer_dict[(CancerDetectionState.UNDETECTED.value, CancerState.DEAD.value)] = [0, 0, 0, 0, 1]
    # --- Once detected, no one changes states
    cancer_dict[(CancerDetectionState.DETECTED.value, CancerState.NORMAL.value)] = [1, 0, 0, 0, 0]
    cancer_dict[(CancerDetectionState.DETECTED.value, CancerState.LOCAL.value)] = [0, 1, 0, 0, 0]
    cancer_dict[(CancerDetectionState.DETECTED.value, CancerState.REGIONAL.value)] = [0, 0, 1, 0, 0]
    cancer_dict[(CancerDetectionState.DETECTED.value, CancerState.DISTANT.value)] = [0, 0, 0, 1, 0]
    cancer_dict[(CancerDetectionState.DETECTED.value, CancerState.DEAD.value)] = [0, 0, 0, 0, 1]

    # ------------------------------------------------------------------------------------------------------------------
    # ----- CancerDetection matrix
    detection_dict = dict()
    detection_dict[CancerState.NORMAL.value] = 0
    detection_dict[CancerState.LOCAL.value] = to_monthly_prob(210.6)
    detection_dict[CancerState.REGIONAL.value] = to_monthly_prob(916.1)
    detection_dict[CancerState.DISTANT.value] = to_monthly_prob(2302.6)
    detection_dict[CancerState.DEAD.value] = 0

    # Save Transition Dictionaries
    with open(transition_dictionary_dir.joinpath("life_dictionary.pickle"), "wb") as handle:
        pickle.dump(life_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
    with open(transition_dictionary_dir.joinpath("hpv_dictionary.pickle"), "wb") as handle:
        pickle.dump(hpv_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
    with open(transition_dictionary_dir.joinpath("hiv_dictionary.pickle"), "wb") as handle:
        pickle.dump(hiv_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
    with open(transition_dictionary_dir.joinpath("cancer_dictionary.pickle"), "wb") as handle:
        pickle.dump(cancer_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
    with open(transition_dictionary_dir.joinpath("cancer_detection_dictionary.pickle"), "wb") as handle:
        pickle.dump(detection_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # ----- Create base scenario examples:
    tdd = transition_dictionary_dir
    copy_tree(tdd, str(experiment_dir.joinpath("scenario_base", "transition_dictionaries")))
    copyfile(base_documents_dir.joinpath("parameters.yml"), experiment_dir.joinpath("scenario_base/parameters.yml"))

    if is_zambia:
        experiment_dir.joinpath("scenario_screening").mkdir(exist_ok=True)
        copy_tree(tdd, str(experiment_dir.joinpath("scenario_screening", "transition_dictionaries")))
        experiment_dir.joinpath("scenario_vaccination").mkdir(exist_ok=True)
        copy_tree(tdd, str(experiment_dir.joinpath("scenario_vaccination", "transition_dictionaries")))

    # ------------------------------------------------------------------------------------------------------------------
    # Lets run a quick check of the HPV keys
    keys = pd.DataFrame(list(hpv_dict.keys()))
    # Age
    ages = keys[0].unique()
    assert min(ages) == 9
    assert max(ages) == 100
    assert len(ages) == 92
    # HPV Strains
    strains = keys[1].unique()
    assert all([strain in [item.value for item in HpvStrain] for strain in strains])
    # Immunity
    imm = keys[2].unique()
    assert all([immunity in [item.value for item in HpvImmunity] for immunity in imm])
    # HpvState
    hpv_states = keys[3].unique()
    assert all([hpv in [item.value for item in HpvState] for hpv in hpv_states])
    # HIV
    hiv_states = keys[4].unique()
    assert all([hiv in [item.value for item in HivState] for hiv in hiv_states])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("country", type=str, default="all", help="Name of the country.")
    args = parser.parse_args()
    main(args)
