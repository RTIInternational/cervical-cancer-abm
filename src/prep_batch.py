import argparse
import importlib
from pathlib import Path

from model.parameters import Parameters


class Scenario:
    def __init__(self, values):
        self.params = Parameters()
        for v in values:
            self.params.update_from_dict(v)


class Values:
    """
    Defines all the different parameter values that may be used by scenarios in
    this experiment.
    """

    base = {
        "num_agents": 100_000,
        "num_steps": 1092,
        "steps_per_year": 12,
        "initial_age": 9,
        "hiv_detection_rate": 1,
        "vaccination": {"schedule": {}, "cost": 15.00},
        "screening": {
            "protocol": "none",
            "age_routine_start": 25,
            "age_routine_end": 49,
            "interval_routine": 5,
            "interval_re_test": 1,
            "interval_surveillance": 1,
            "interval_hiv": 3,
            "via": {"sensitivity": 0.73, "specificity": 0.75, "cost": 3.00},
            "dna": {"sensitivity": 0.90, "specificity": 0.57, "cost": 18.00},
            "cancer_inspection": {"sensitivity": 1.00, "specificity": 1.00, "cost": 3.00},
            "compliance": {"never": 0.2, "never_surveillance": 0.0},
        },
        "treatment": {
            "cryo": {"proportion": 0.85, "effectiveness": 0.88, "cost": 2.00},
            "leep": {"proportion": 0.15, "effectiveness": 0.94, "cost": 32.00},
            "cancer_cost_local": 1186.00,
            "cancer_cost_regional": 1389.00,
            "cancer_cost_distant": 1146.00,
        },
    }

    vaccinate_80 = {
        "vaccination": {"schedule": {9: 0.8}},
    }

    vaccinate_50 = {
        "vaccination": {"schedule": {9: 0.5}},
    }

    vaccinate_20 = {
        "vaccination": {"schedule": {9: 0.2}},
    }

    via = {
        "screening": {"protocol": "via"},
    }

    dna_then_via = {
        "screening": {"protocol": "dna_then_via"},
    }

    dna_then_triage = {
        "screening": {"protocol": "dna_then_triage"},
    }

    dna_then_treat = {
        "screening": {"protocol": "dna_then_treatment"},
    }

    performance_low = {
        "screening": {"via": {"sensitivity": 0.63, "specificity": 0.75}, "dna": {"sensitivity": 0.69}},
    }

    performance_high = {
        "screening": {"via": {"sensitivity": 0.84, "specificity": 0.85}, "dna": {"sensitivity": 0.99}},
    }

    interval_10 = {
        "screening": {
            "interval_routine": 10,
            "interval_hiv": 10,
            "interval_re_test": 10,
            "interval_surveillance": 10,
            "compliance": {"never_surveillance": 0},
        },
    }

    screen_at_35_only = {
        "screening": {
            "age_routine_start": 35,
            "age_routine_end": 35,
            "interval_routine": 100,
            "interval_hiv": 100,
            "interval_re_test": 100,
            "interval_surveillance": 100,
        },
    }

    compliance_60 = {
        "screening": {"compliance": {"never": 0.4}},
    }

    compliance_40 = {
        "screening": {"compliance": {"never": 0.6}},
    }


def main(batch: str, country: str):
    batch_dir = Path(f"batches/{batch}")
    experiment_dir = Path(f"experiments/{country}")

    config = importlib.import_module("{}.config".format(str(batch_dir).replace("/", ".")))

    for name in config.scenarios:
        # Create the scenario directory
        scenario = config.scenarios[name]
        scenario_dir = experiment_dir.joinpath(batch, f"scenario_{name}")
        scenario_dir.mkdir(exist_ok=True, parents=True)

        # Save the parameters file
        params_file = scenario_dir.joinpath("parameters.yml")
        scenario.params.export_to_file(params_file)

        # Save the pickle files
        pickles = experiment_dir.joinpath("transition_pickles/")
        for source in pickles.iterdir():
            if source.name.isnumeric():
                # Create the iteration directory
                iteration_dir = scenario_dir.joinpath(f"iteration_{source.name}")
                iteration_dir.mkdir(exist_ok=True, parents=True)
                # Create the transition directory
                transition_dir = iteration_dir.joinpath("transition_dictionaries")
                transition_dir.mkdir(exist_ok=True)

                # Save the pickles as alias files
                for dict_name in ["cancer_detection", "cancer", "hpv", "hiv", "life"]:
                    dst = transition_dir.joinpath(dict_name + "_dictionary.pickle")
                    src = source.joinpath("transition_dictionaries", dict_name + "_dictionary.pickle")
                    try:
                        try:
                            dst.unlink()
                        except Exception as E:
                            E
                        dst.symlink_to(src.resolve())
                    except Exception as E:
                        E  # Do nothing - link already exists


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create all input files for a batch of scenarios")
    parser.add_argument("batch", type=str, help="name of the batch directory")
    parser.add_argument("--country", type=str, default="all", help="The directory containing the experiment")
    args = parser.parse_args()

    if args.country == "all":
        run_list = []
        for country in ["zambia", "japan", "usa", "india"]:
            main(batch=args.batch, country=country)
    else:
        main(batch=args.batch, country=args.country)
