import pickle
import shutil
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from model.misc_functions import normalize
from model.state import AgeGroup, CancerState, HivState, HpvImmunity, HpvState, HpvStrain


def create_multipliers(df: pd.DataFrame, rng: np.random.RandomState = None, use_selected: bool = False) -> list:
    """Create a list of multipliers to use in a scenario

    Args:
        df (pd.DataFrame): [...]
        rng (np.random.RandomState, optional): [...]. Defaults to None.
        use_selected (bool, optional): [Use the middle of the triangle distribution or not]. Defaults to False.

    Returns:
        [list]: A list of multipliers
    """
    multipliers = []
    for _, row in df.iterrows():
        if use_selected | (row.IMMUNITY == "VACCINE"):
            multiplier = float(row.Selected)
        else:
            mode = float(row.Selected)
            if mode != 0:
                multiplier = rng.triangular(left=row.Low, mode=mode, right=row.High)
            else:
                multiplier = 0
        multipliers.append(multiplier)

    return multipliers


def create_tested_multipliers(df: pd.DataFrame, rng: np.random.RandomState) -> list:
    """Create a random list of multipliers to use in a scenario that pass all tests

    Args:
        df (pd.DataFrame): [...]
        rng (np.random.RandomState): [...]

    Returns:
        list: [...]
    """

    # Step #1: Load in the previously created models
    directory = Path("experiments/zambia/results/first_pass")
    with open(directory.joinpath("models.pickle"), "rb") as handle:
        models = pickle.load(handle)
    with open(directory.joinpath("target_dict.pickle"), "rb") as handle:
        t_dict = pickle.load(handle)

    test_pass = False
    multipliers = []
    while not test_pass:
        # Step 2: Select random multipliers
        multipliers = create_multipliers(df, use_selected=False, rng=rng)

        test_pass = True
        for key in models.keys():
            model = models[key]
            est = model["model"].predict(np.array([multipliers[i] for i in t_dict[key]["multipliers"]]).reshape(1, -1))[
                0
            ]
            if est < model["cutoff"]:
                continue
            else:
                test_pass = False
    return multipliers


def create_list_of_updates(df: pd.DataFrame, multipliers: list) -> list:
    """Given a list of multipliers and a dataframe of update details - create the list of multiplier updates

    Args:
        df (pd.DataFrame): [...]
        multipliers (list): [...]

    Returns:
        list: [...]
    """
    updates = []
    for i, row in df.iterrows():
        item = {
            "multiplier": multipliers[i],
            "strain": HpvStrain[row["STRAIN"]].value,
            "from": HpvState[row["FROM_STATE"]].value,
            "to": HpvState[row["TO_STATE"]].value,
        }
        if "All" != row["IMMUNITY"]:
            item["immunity"] = HpvImmunity[row["IMMUNITY"]].value
        if "All" != row["HIV"]:
            item["hiv"] = HivState.HIV.value
        updates.append(item)
    return updates


def find_all_keys(keys: list, filters: dict) -> list:
    """Given a list of keys and a dictionary of filters, find all keys that match these filters

    Args:
        keys (list): [...]
        filters (dict): [...]

    Returns:
        list: A list of keys that match the filters
    """
    final_keys = keys
    for k, v in filters.items():
        final_keys = [key for key in final_keys if key[k] in v]

    return final_keys


def save_cancer(baseline_dir: Path, scenario_dir: Path) -> None:
    """Save the Cancer dictionaries as pickles

    Args:
        baseline_dir [Path]: [...]
        scenario_dir [Path]: [...]
    """
    for item in ["cancer", "cancer_detection"]:
        shutil.copyfile(
            baseline_dir.joinpath(item + "_dictionary.pickle"),
            scenario_dir.joinpath("transition_dictionaries/" + item + "_dictionary.pickle"),
        )


def update_and_save_life(baseline_dir: Path, scenario_dir: Path) -> None:
    """Save the life dictionary as a pickle

    Args:
        baseline_dir [Path]: [...]
        scenario_dir [Path]: [...]
    """
    with open(baseline_dir.joinpath("life_dictionary.pickle"), "rb") as handle:
        life_dict = pickle.load(handle)
    life_multiplier = pd.read_csv(baseline_dir.parent.joinpath("base_documents/life_multiplier.csv")).Value[0]
    for k, v in life_dict.items():
        if k[2] == CancerState.NORMAL.value:
            life_dict[k] = v * (1 / life_multiplier)
    with open(scenario_dir.joinpath("transition_dictionaries/life_dictionary.pickle"), "wb") as handle:
        pickle.dump(life_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)


def update_hiv(hiv_dict: dict) -> dict:
    """Update the HIV probabilities using the HIV multipliers

    Args:
        hiv_dict (dict): [...]

    Returns:
        [dict]: An updated dictionary of HIV probabilities
    """
    hiv_multipliers = pd.read_csv("experiments/zambia/base_documents/hiv_multipliers.csv")
    age_ranges = []
    for _, row in hiv_multipliers.iterrows():
        age = row.Age
        if "+" in age:
            age_ranges.append([i for i in range(int(age.split("+")[0]), 100)])
        if "_" in age:
            age_ranges.append([i for i in range(int(age.split("_")[0]), int(age.split("_")[1]) - 1)])
    # --- Use the multipliers to update the transitions
    for key in hiv_dict.keys():
        for _, age_range in enumerate(age_ranges):
            if key[0] in age_range:
                hiv_dict[key] *= hiv_multipliers.loc[_, "Current"]
    # --- Make sure probabilities are less then 1
    if max(hiv_dict.values()) > 1:
        raise ValueError("HIV Probabilities are greater than 1. Check your multipliers.")
    return hiv_dict


def update_and_save_hiv(baseline_dir: Path, scenario_dir: Path) -> None:
    """Save the HIV dictionary as a pickle

    Args:
        baseline_dir [Path]: [...]
        scenario_dir [Path]: [...]
    """
    with open(baseline_dir.joinpath("hiv_dictionary.pickle"), "rb") as handle:
        hiv_dict = pickle.load(handle)
    if "zambia" in str(scenario_dir):
        hiv_dict = update_hiv(hiv_dict=hiv_dict)
    with open(scenario_dir.joinpath("transition_dictionaries/hiv_dictionary.pickle"), "wb") as handle:
        pickle.dump(hiv_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)


def update_hpv(hpv_dict: dict, base_updates: list, cm_df: pd.DataFrame) -> dict:
    """ Update the HPV probabilty dictionary using a list of updates
    """
    hpv_dict_copy = deepcopy(hpv_dict)

    # ----- BASE MULTIPLIER UPDATES ------------------------------------------------------------------------------------
    # Create the filters for each multiplier. This is based on the keys for the the dictionary
    # 0: Age, 1: HpvStrain, 2: HpvImmunity, 3: HpvState, 4: HivState
    for update in base_updates:
        filters = {
            1: [update["strain"]],
            3: [update["from"]],
        }
        if "immunity" in update:
            filters[2] = [update["immunity"]]
        if "hiv" in update:
            filters[4] = [update["hiv"]]

        keys = find_all_keys(hpv_dict.keys(), filters)
        # Find the element of the list to update
        to_value = update["to"] - 1
        # Multiple probability by the multiplier`
        for key in keys:
            # If Immunity - the value should be (1 - current value), as this is a percent reduction
            multiplier = update["multiplier"]
            if "immunity" in update:
                multiplier = 1 - multiplier
            hpv_dict_copy[key][to_value] = hpv_dict_copy[key][to_value] * multiplier

    # ----- Normalize all of the probabilities back to 1
    for key in hpv_dict_copy.keys():
        hpv_dict_copy[key] = normalize(hpv_dict_copy[key], return_cdf=False)

    # ----- CURVE MULTIPLIER UPDATES -----------------------------------------------------------------------------------
    age_ranges = []
    for age_range in cm_df.Age.values:
        if "<" in age_range:
            age_ranges.append([i for i in range(9, int(age_range[1:]))])
        elif "+" in age_range:
            age_ranges.append([i for i in range(int(age_range[:-1]), 101)])
        else:
            a = age_range.split("_")
            age_ranges.append([i for i in range(int(a[0]), int(a[1]))])

    for age in AgeGroup:
        age = age.value
        index = [age in r for r in age_ranges]

        value = "AGE_" + str(age)
        temp_df = cm_df.loc[index]
        temp_df = temp_df[(temp_df["Current"] != 0)]

        for _, temp_row in temp_df.iterrows():
            # ----- HPV
            if temp_row.State == "HPV":
                # This singular multiple effects 2 rows
                combinations = [
                    (HpvState.NORMAL.value, HpvState.HPV.value),  # 1. Normal -> HPV
                    (HpvState.HPV.value, HpvState.NORMAL.value),  # 2. HPV -> NORMAL
                ]
                for combo in combinations:
                    filters = {
                        0: [AgeGroup[value].value],  # Age
                        1: [HpvStrain[temp_row.Strain].value],  # HPV Strain
                        3: [combo[0]],  # Current Hpv State
                    }
                    if temp_row.HIV != "ALL":
                        filters[4] = [HivState[temp_row.HIV].value]  # HIV

                    keys = find_all_keys(hpv_dict.keys(), filters)
                    list_location = combo[1] - 1
                    multiplier = temp_row["Current"]
                    if combo[1] < combo[0]:
                        multiplier = 1 / temp_row["Current"]
                    for key in keys:
                        hpv_dict_copy[key][list_location] *= multiplier

            # ----- CIN23
            if temp_row.State == "CIN23":
                # This singular multiple effects 4 rows
                combinations = [
                    (HpvState.HPV.value, HpvState.CIN_2_3),  # 2. HPV -> CIN_2_3
                    (HpvState.CIN_1.value, HpvState.CIN_2_3.value),  # 3. CIN_1 -> CIN_2_3
                    (HpvState.CIN_2_3.value, HpvState.CIN_1.value),  # 4. CIN_2_3 -> CIN_1
                    (HpvState.CIN_2_3.value, HpvState.NORMAL.value),  # 5. CIN_2_3 -> NORMAL
                ]
                for combo in combinations:
                    filters = {
                        0: [AgeGroup[value].value],  # Age
                        1: [HpvStrain[temp_row.Strain].value],  # HPV Strain
                        3: [combo[0]],  # Current Hpv State
                        4: [HivState[temp_row.HIV].value],  # HIV
                    }
                    keys = find_all_keys(hpv_dict.keys(), filters)
                    list_location = combo[1] - 1
                    multiplier = temp_row["Current"]
                    if combo[1] < combo[0]:
                        multiplier = 1 / temp_row["Current"]
                    for key in keys:
                        hpv_dict_copy[key][list_location] *= multiplier

            # ----- CANCER
            if temp_row.State == "CANCER":
                # This singular multiple effects 1 row
                filters = {
                    0: [AgeGroup[value].value],  # Age
                    3: [HpvState.CIN_2_3.value],  # Current Hpv State
                }
                keys = find_all_keys(hpv_dict.keys(), filters)
                multiplier = temp_row["Current"]
                list_location = HpvState.CANCER.value - 1
                for key in keys:
                    hpv_dict_copy[key][list_location] *= multiplier

    # ----- Normalize all of the probabilities back to 1
    for key in hpv_dict_copy.keys():
        hpv_dict_copy[key] = normalize(probability_list=hpv_dict_copy[key], return_cdf=False)

    return hpv_dict_copy


def update_and_save_hpv(baseline_dir: Path, scenario_dir: Path, base_updates: list, cm_df: pd.DataFrame):
    """Update and Save the HPV dictionary as a pickle

    Args:
        baseline_dir [Path]: [...]
        scenario_dir [Path]: [...]
        updates [list]: [...]
    """

    with open(baseline_dir.joinpath("hpv_dictionary.pickle"), "rb") as handle:
        hpv_dict = pickle.load(handle)

    hpv_dict = update_hpv(hpv_dict, base_updates, cm_df)

    with open(scenario_dir.joinpath("transition_dictionaries/hpv_dictionary.pickle"), "wb") as handle:
        pickle.dump(hpv_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)


def prepare_scenario(
    experiment_dir: Path,
    scenario_dir: Path,
    cm_df: pd.DataFrame,
    use_selected: bool = False,
    test_multipliers: bool = False,
    seed: int = 1111,
    num_agents: int = 100_000,
):
    """ Prepare a scenario
    """

    # ----- Create scenario and transition dictionary directories
    scenario_dir.mkdir(exist_ok=True)
    scenario_dir.joinpath("transition_dictionaries").mkdir(exist_ok=True)

    # --- Copy over parameters file
    with experiment_dir.joinpath("base_documents/parameters.yml").open(mode="r") as f:
        params = yaml.safe_load(f)
    params["num_agents"] = num_agents
    with open(scenario_dir.joinpath("parameters.yml"), "w") as f:
        yaml.dump(params, f)

    # ----- Save the Transition Files ----------------------------------------------------------------------------------
    baseline_dir = experiment_dir.joinpath("transition_dictionaries")
    # --- Copy other dictionaries that did not change
    save_cancer(baseline_dir, scenario_dir)
    update_and_save_life(baseline_dir, scenario_dir)
    update_and_save_hiv(baseline_dir, scenario_dir)

    rng = np.random.RandomState(seed)

    # ----- Select base multipliers
    df = pd.read_csv(scenario_dir.parent.joinpath("base_documents/multipliers.csv"))
    df["Selected"] = df.Peak
    if test_multipliers:
        multipliers = create_tested_multipliers(df, rng)
        base_updates = create_list_of_updates(df, multipliers=multipliers)
    else:
        multipliers = create_multipliers(df, rng=rng, use_selected=use_selected)
        base_updates = create_list_of_updates(df, multipliers=multipliers)

    # --- Save selected multipliers
    multipliers = [scenario_dir.name] + multipliers
    pd.DataFrame(multipliers).transpose().to_csv(scenario_dir.joinpath("selected_multipliers.csv"), index=False)

    update_and_save_hpv(baseline_dir, scenario_dir, base_updates, cm_df)
