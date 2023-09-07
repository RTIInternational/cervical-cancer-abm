import argparse
from pathlib import Path

from model.logger import LoggerFactory

from src.helper_functions import multi_process, str_to_bool, read_cm
from src.prep_scenario import prepare_scenario


def main(args):
    experiment_dir = Path(f"experiments/{args.country}")

    logger_factory = LoggerFactory()
    logger = logger_factory.create_logger(experiment_dir.joinpath("mass_run_prep.log"))

    cm_df = read_cm(experiment_dir)

    run_list = []
    for run_i in range(args.n):
        run_list.append(
            {
                "experiment_dir": experiment_dir,
                "scenario_dir": experiment_dir.joinpath("scenario_{:04}".format(run_i)),
                "cm_df": cm_df,
                "use_selected": False,
                "test_multipliers": str_to_bool(args.test_params),
                "seed": run_i,
                "num_agents": args.num_agents,
            }
        )
    multi_process(prepare_scenario, run_list, logger, "scenario_dir")


if __name__ == "__main__":
    """ Prepare a large amount of scenarios. The goal is to test different parameter sets and see how the runs do
    compared a country's target values.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("country", type=str, default="all", help="Name of the country.")
    parser.add_argument("--num_agents", default=100_000)
    parser.add_argument("--n", type=int, default=10, help="number of runs to generate (default: %(default)s)")
    parser.add_argument(
        "--test_params", type=str, default="False", help="Should parameters be tested?. (default: %(default)s)"
    )
    args = parser.parse_args()

    main(args)
