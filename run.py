import argparse
import multiprocessing
import random
from pathlib import Path

from model.cervical_model import CervicalModel
from model.logger import LoggerFactory
from src.run_mass_runs import get_run_analysis


class Runner:
    def __init__(self, directory: str, cpus: int, num_iterations: int, seed: int = 1111):
        self.directory = Path(directory)
        self.cpus = cpus
        self.num_iterations = num_iterations
        self.seed = seed
        self.logger_factory = LoggerFactory()
        self.is_experiment = not self.directory.name.startswith("scenario")
        self.logger = self.logger_factory.create_logger(self.directory.joinpath("run.log"))

        self.rng = random.Random()
        self.rng.seed(seed)

        if self.is_experiment:
            self.scenario_dirs = [d for d in self.directory.iterdir() if d.is_dir() and d.name.startswith("scenario")]
        else:
            self.scenario_dirs = [self.directory]

    def run(self):
        self.logger.info("Running simulation in directory: {}".format(self.directory))
        self.logger.info("Random seed: {}".format(self.seed))

        with multiprocessing.Pool(self.cpus) as pool:

            tasks = []
            for directory in self.scenario_dirs:
                self.logger.info("Adding scenario [{}] to queue".format(directory.name))
                for task in self._get_scenario_tasks(directory, pool):
                    tasks.append(task)

            pool.close()

            self.logger.info("Executing all tasks in queue")

            errors = 0
            for task in tasks:
                try:
                    task["result"].get()
                except Exception as e:
                    errors += 1
                    self.logger.error(
                        "Exception in scenario [{}], iteration [{}]".format(task["scenario"], task["iteration"])
                    )
                    self.logger.exception(e)

            pool.join()

        if errors > 0:
            print("{} iterations exited with errors. See log for details.".format(errors))

        self.logger.info("All tasks complete")

    def _get_scenario_tasks(self, directory, pool):
        for iteration in range(self.num_iterations):
            self.logger.debug("Adding iteration [{}] to queue".format(iteration))
            yield {
                "scenario": directory.name,
                "iteration": iteration,
                "result": pool.apply_async(
                    func=run_iteration,
                    kwds=dict(
                        scenario_dir=directory,
                        iteration=iteration,
                        logger_factory=self.logger_factory,
                        seed=self.rng.randint(1, 2 ** 30),
                    ),
                ),
            }


def run_iteration(scenario_dir: Path, logger_factory: LoggerFactory, iteration: int, seed: int = 1111):

    iteration_dir = scenario_dir.joinpath(f"iteration_{iteration}")
    iteration_dir.mkdir(exist_ok=True)
    logger = logger_factory.create_logger(iteration_dir.joinpath("iteration.log"))

    try:
        logger.info("Initializing the model")
        model = CervicalModel(scenario_dir=scenario_dir, iteration=iteration, logger=logger, seed=seed)

        logger.info("Running the model")
        model.run()

        logger.info("Analyzing the model")
        run_analysis = get_run_analysis(scenario_dir)
        run_analysis(scenario_dir, 0)

    except Exception as e:
        logger.exception(e)
        raise

    logger.info("Complete")


if __name__ == "__main__":
    description = """ Run a model experiment or scenario. If the name of input_dir starts with "scenario", then treat
    it as a scenario directory and run that scenario. Otherwise, treat it as an experiment directory by finding all the
    scenario subdirectories and running those scenarios."""

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("input_dir", help="directory containing the experiment or scenario")
    parser.add_argument(
        "--n", type=int, default=1, help="number of iterations to run for each scenario (default: %(default)s)"
    )
    parser.add_argument(
        "--cpus", type=int, default=1, help="number of CPUs to use simultaneously (default: %(default)s)"
    )
    parser.add_argument(
        "--seed", type=int, default=1111, help="seed for the random number generator (default: %(default)s)"
    )
    args = parser.parse_args()

    print(args)
    runner = Runner(directory=args.input_dir, cpus=args.cpus, num_iterations=args.n, seed=args.seed,)
    runner.run()
