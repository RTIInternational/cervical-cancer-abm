"""
The goal of this script is to run the "base" scenario, as well as "vacinated_80" - 10 times using 10 different seeds.
The results should be aggregated at the same time.
"""

from pathlib import Path

import pandas as pd
from model.cervical_model import CervicalModel
from model.logger import LoggerFactory

from src.analyze import analyze
from src.helper_functions import multi_process


def run_and_analyze(scenario_dir, iteration: str, seed: int):
    print("Running scenario: {}, run: {}, seed: {}".format(scenario_dir, str(iteration), str(seed)))
    model = CervicalModel(scenario_dir, iteration, logger=LoggerFactory().create_logger(), seed=seed)
    model.run()
    analyze(scenario_dir, iteration)


def main():
    batch_dir = Path("experiments/zambia/batch_10")

    logger_factory = LoggerFactory()
    logger = logger_factory.create_logger(batch_dir.joinpath("variance_analysis.log"))

    scenario_dirs = ["scenario_base", "scenario_vaccinate[80]"]
    seeds = [i for i in range(1111, 1121)]

    output = []
    for seed in seeds:
        # ----- Make a list of runs
        run_list = []
        for item in scenario_dirs:
            for iteration in batch_dir.joinpath(item).iterdir():
                if "iteration" in str(iteration.name):
                    scenario_dir = batch_dir.joinpath(item)
                    run_list.append(
                        {
                            "scenario_dir": scenario_dir,
                            "iteration": iteration.name.replace("iteration_", ""),
                            "seed": seed,
                        }
                    )

        # ----- Run the scenarios
        multi_process(run_and_analyze, run_list, logger, "scenario_dir")

        # Collect all the individual results files into a single data structure.
        for run in run_list:
            result = pd.read_csv(batch_dir.joinpath(run[0], f"iteration_{run['iteration']}", "results.csv"))
            output.append((run[0], run[1], seed, result.lifespan.values[0]))

    df = pd.DataFrame(output)
    df.columns = ["Scenario", "Iteration", "Seed", "Lifespan"]
    df.to_csv(batch_dir.joinpath("variance_analysis.csv"), index=False)


def analysis_output():
    batch_dir = Path("experiments/zambia/batch_10")
    df = pd.read_csv(batch_dir.joinpath("variance_analysis.csv"))

    ls = df.groupby(by=["Scenario", "Seed"])["Lifespan"]
    c1 = ls.mean()
    c2 = ls.std()
    c3 = ls.min()
    c4 = ls.max()

    result = pd.concat([c1, c2, c3, c4], axis=1)
    result.columns = ["Mean", "Std", "Min", "Max"]
    result = result.reset_index()
    result.to_csv(batch_dir.joinpath("variance_analysis_view1.csv"))

    ls2 = result.groupby(["Scenario"])["Mean"]
    c1 = ls2.mean()
    c2 = ls2.std()
    c3 = ls2.min()
    c4 = ls2.max()

    result2 = pd.concat([c1, c2, c3, c4], axis=1)
    result2.columns = ["Mean", "Std", "Min", "Max"]
    result2.to_csv(batch_dir.joinpath("variance_analysis_view2.csv"))


if __name__ == "__main__":
    main()
