import argparse
from pathlib import Path

from model.cervical_model import CervicalModel
from model.logger import LoggerFactory

from src.analyze import analyze
from src.helper_functions import multi_process


def run_and_analyze(scenario_dir, iteration, seed):
    # Setup & Run Model
    model = CervicalModel(scenario_dir, iteration, logger=LoggerFactory().create_logger(), seed=seed)
    model.run()
    # Analyze Model
    analyze(scenario_dir, int(iteration))


def main(country: str, batch: str, seed: int):
    experiment_dir = Path(f"experiments/{country}")
    batch_dir = experiment_dir.joinpath(batch)
    logger_factory = LoggerFactory()
    logger = logger_factory.create_logger(batch_dir.joinpath("run.log"))

    # Get list of all scenarios and runs:
    run_list = []
    for scenario_dir in batch_dir.iterdir():
        if "scenario_" in scenario_dir.name:
            for iteration_i in scenario_dir.iterdir():
                if "iteration" in iteration_i.name:
                    run_list.append(
                        {
                            "scenario_dir": scenario_dir,
                            "iteration": iteration_i.name.replace("iteration_", ""),
                            "seed": int(seed),
                        }
                    )

    # ----- Run the scenarios
    multi_process(run_and_analyze, run_list, logger, "scenario_dir")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", help="name of the batch directory")
    parser.add_argument("--country", type=str, default="all", help="The directory containing the experiment")
    parser.add_argument("--seed", type=int, default=1111, help="The seed for the run")
    args = parser.parse_args()

    if args.country == "all":
        run_list = []
        for country in ["zambia", "japan", "usa", "india"]:
            main(batch=args.batch, country=country, seed=args.seed)
    else:
        main(batch=args.batch, country=args.country, seed=args.seed)
