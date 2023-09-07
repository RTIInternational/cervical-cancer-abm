""" This script will walk you through building predictive models for each target.

Based on 5,000 previous runs, can we predict how well a parameter set will do for a specific target before the set
is ran in a model? If so, let's reduce the number of necessary models by building predictive models first.

"""

import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from matplotlib import pyplot as plt
from ast import literal_eval


def make_model(target_id: str, show: bool = False):
    """ Make a random forest modeling - predicting the target error based on the multipliers selected

    Args:
        target_id (str): The target ID of the target we are modeling
        show (bool, optional):  True to print the scatter plot. Defaults to True.
    Returns:
        clf (random forest classifier)
        pred (the predictions, if output_all=True),
        best_cutoff (float of cutoff)
    """
    df = selected_multipliers.loc[t_dict[target_id]["multipliers"], :].T.reset_index()
    df = df.rename(columns={"index": "Scenario"})
    df = difference_df[["Scenario", target_id]].merge(df, left_on="Scenario", right_on="Scenario")

    # Select y
    y = np.array(df[target_id]).astype(float)
    # Split into training/testing
    x_train, x_test, y_train, y_test = train_test_split(df.iloc[:, 2:], y, test_size=0.33, random_state=1111)
    # Run RF
    clf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=1111)
    clf.fit(x_train, y_train)
    pred = clf.predict(x_test)
    mse = mean_squared_error(y_test, pred)
    print("MSE for " + target_id + ": " + str(mse))

    # Find a cutoff such that only 60% of the parameters pass
    cutoff = np.quantile(pred, 0.6)
    print("Percent of tests accepted: " + str(round(len(pred[pred < cutoff]) / len(pred), 3)) + ".")
    print("Cutoff is: {}".format(cutoff))

    if show:
        plt.plot(pred, y_test, "o", markersize=2)
        plt.axvline(x=cutoff)
    return {"model": clf, "predicted_values": pred, "cutoff": cutoff}


if __name__ == "__main__":

    # Read Values
    directory = Path("experiments/zambia/results/first_pass")
    selected_multipliers = pd.read_csv(directory.joinpath("selected_multipliers.csv"))
    analysis_output = pd.read_csv(directory.joinpath("analysis_output.csv"))
    analysis_values = pd.read_csv(directory.joinpath("analysis_values.csv")).drop(["Unnamed: 0"], axis=1)
    targets_df = pd.read_csv("experiments/zambia/base_documents/targets.csv")
    multipliers_df = pd.read_csv("experiments/zambia/base_documents/multipliers.csv")

    # Target Dictionary: Which multiplier effects which target?
    t_dict = {item: {item2: list() for item2 in ["targets", "multipliers"]} for item in targets_df.Category_ID.unique()}
    for i, row in enumerate(multipliers_df["Effects"].values):
        a_list = literal_eval(row)
        for item in a_list:
            t_dict[item]["multipliers"].append(i)
    t_dict["CancerInc"]["multipliers"] = [i for i in range(0, 45)]
    t_dict["Cause"]["multipliers"] = [i for i in range(0, 45)]
    for i, target in enumerate(targets_df.Category_ID):
        t_dict[target]["targets"].append(i)

    # Loop though the targets and calculate how close each scenario was to that target
    difference_df = pd.DataFrame(analysis_output["Scenario"])
    for i in t_dict:
        avg_diff = []
        target_rows = t_dict[i]["targets"]
        multiplier_rows = t_dict[i]["multipliers"]
        targets = targets_df.loc[target_rows, "Value"].values

        comparison_values = analysis_values.loc[target_rows, :].T

        for _, row in comparison_values.iterrows():
            avg_diff.append(abs(row.values - targets).mean())

        difference_df[i] = avg_diff

    # Run a model for each target
    models = {}
    for target_id in t_dict.keys():
        if target_id in ["HIV", "CancerInc"]:
            continue
        else:
            models[target_id] = make_model(target_id=target_id)

    # Save Files
    with open(directory.joinpath("models.pickle"), "wb") as handle:
        pickle.dump(models, handle)
    with open(directory.joinpath("target_dict.pickle"), "wb") as handle:
        pickle.dump(t_dict, handle)
    # With 60% for each test passing, and 13 tests, we should get a passing test every 800 parameter sets
    print("Only 1 out of {} parameter sets will be ran.".format(str(1 / (0.6 ** 13))))

    # THE REST OF THIS IS JUST FOR TESTING PURPOSES. IT WILL TELL US HOW MANY SETS OF MULTIPLIERS ARE BEING ACCEPTED
    # About 50-60% of the factors should be rejected for each model
    count = [0] * len(models.keys())
    runs = 1000
    for j in range(runs):
        multipliers = []
        for _, row in multipliers_df.iterrows():
            if row.IMMUNITY == "VACCINE":
                multiplier = float(row.Selected)
            else:
                mode = float(row.Triangle_Mode)
                if mode != 0:
                    multiplier = np.random.triangular(left=row.Triangle_Low, mode=mode, right=row.Triangle_High)
                else:
                    multiplier = 0
            multipliers.append(multiplier)
        m = multipliers
        for i, key in enumerate(models.keys()):
            if key in ["HIV", "CancerInc"]:
                "do nothing"
            else:
                t = models[key]
                pred = t["model"].predict(np.array([m[i] for i in t_dict[key]["multipliers"]]).reshape(1, -1))[0]
                if pred < t["cutoff"]:
                    count[i] = count[i] + 1
    print(f"Proportion of each test that passes: {[count[i]/runs for i in range(len(count))]}.")
