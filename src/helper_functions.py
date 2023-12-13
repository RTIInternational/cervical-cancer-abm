import multiprocessing
import math
from pathlib import Path

import pandas as pd


def combine_age_groups(df, ages, target):
    average = []
    for i in range(len(ages) - 1):
        age_range = range(ages[i], ages[i + 1])
        value = round(df.loc[age_range].mean(), 4)
        average.append(value)

    age = []
    for i in range(len(ages) - 2):
        age.append(str(ages[i]) + "_" + str(ages[i + 1]))
    age.append(str(ages[len(ages) - 2]) + "+")

    df_final = pd.DataFrame()
    df_final["Age"] = age
    df_final["Model"] = average
    df_final.insert(loc=0, column="Target", value=target)

    return df_final


def get_pool_count():
    """Return a reasonable CPU count to use
    """
    pool_count = math.floor(multiprocessing.cpu_count() * 0.85)

    return pool_count


def multi_process(a_function, run_list, logger, info_id):
    pool_count = get_pool_count()
    with multiprocessing.Pool(pool_count) as pool:
        tasks = []
        for item in run_list:
            tasks.append({"run_dictionary": item, "result": pool.apply_async(func=a_function, kwds=item)})
        pool.close()
        for task in tasks:
            info = task["run_dictionary"][info_id]
            logger.info(f"Processing: {info}.")
            try:
                task["result"].get()
            except Exception as E:
                logger.info(f"Problem running {info}. Exception was: {E}")
        pool.join()


def str_to_bool(string):
    if string == "True":
        return True
    elif string == "False":
        return False
    return ValueError(f"The value you provided: '{string}' is not allowed.")


def read_cm(experiment_dir: Path):
    return pd.read_csv(experiment_dir.joinpath("base_documents/curve_multipliers.csv"))
