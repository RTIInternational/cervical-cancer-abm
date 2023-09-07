import argparse
from pathlib import Path

import pandas as pd
from model.analysis import Analysis
from model.event import Event
from model.parameters import Parameters
from model.state import CancerDetectionState, CancerState, HivState, LifeState

AGE_RANGES = (
    (0, 100),
    (0, 49),
    (0, 69),
    (0, 4),
    (5, 9),
    (10, 14),
    (15, 19),
    (20, 24),
    (25, 29),
    (30, 34),
    (35, 39),
    (40, 44),
    (45, 49),
    (50, 54),
    (55, 59),
    (60, 64),
    (65, 69),
    (70, 74),
    (75, 79),
    (80, 100),
)


def analyze(scenario_dir: Path, iteration: int = 0):
    iteration_dir = scenario_dir.joinpath(f"iteration_{iteration}")
    print(f"Analyzing iteration {str(iteration_dir)}")
    iteration_path = Path(iteration_dir)
    params = Parameters()
    params.update_from_file(iteration_path.parent.joinpath("parameters.yml"))

    agent_index = pd.Index(range(params.num_agents))

    # Read all of the state changes
    temp_df = pd.read_parquet(iteration_path.joinpath("state_changes.parquet"))

    # At what time did each agent die?
    death_time = temp_df[temp_df.State == LifeState.id][["Time", "Unique_ID"]]
    death_time = (
        death_time.set_index("Unique_ID")
        .rename(columns={"Time": "death_time"})
        .reindex(agent_index)
        .fillna(params.num_steps)
    )
    # At what time did each agent get cancer?
    cancer_time = temp_df[temp_df.State == CancerDetectionState.id][["Time", "Unique_ID"]]
    cancer_time = cancer_time.set_index("Unique_ID").rename(columns={"Time": "cancer_time"}).reindex(agent_index)
    # At what time did each agent get cancer?
    hiv_time = temp_df[temp_df.State == HivState.id][["Time", "Unique_ID"]]
    hiv_time = hiv_time.set_index("Unique_ID").rename(columns={"Time": "hiv_time"}).reindex(agent_index)

    agents = pd.concat(objs=(death_time, cancer_time, hiv_time), axis=1,)

    # Compute the age in years. We're rounding to help avoid floating point issues when using these ages later.
    for field in ("death", "cancer", "hiv"):
        agents[f"{field}_age"] = params.initial_age + (agents[f"{field}_time"] / params.steps_per_year).round(3)
    # Compute if agent got cancer or hiv
    for field in ("cancer", "hiv"):
        agents[f"got_{field}"] = pd.notnull(agents[f"{field}_time"])

    # Create booleans for each
    for ages in AGE_RANGES:
        rng = f"{ages[0]}_{ages[1]}"
        agents[f"alive_{ages[0]}"] = agents["death_age"] >= ages[0]
        agents[f"cancer_{rng}"] = (
            agents["got_cancer"] & (agents["cancer_age"] >= ages[0]) & (agents["cancer_age"] < ages[1] + 1)
        )
        agents[f"cancer_death_{rng}"] = agents[f"cancer_{rng}"] & (agents["death_age"] - agents["cancer_age"] <= 5)

    # ------------------------------------------------------------------------------------------------------------------
    # Gather the cost data.

    costs = pd.read_parquet(iteration_path.joinpath("events.parquet"))
    # Calculate age
    costs["Age"] = params.initial_age + costs["Time"] / params.steps_per_year

    # Create column of costs for each event
    for e in Event:
        costs[f"cost_{e.name.lower()}"] = costs["Cost"].where(costs["Event"] == e.value, other=0,)

    # Calculate when the cost occurred
    for ages in AGE_RANGES:
        rng = f"{ages[0]}_{ages[1]}"
        costs[f"cost_{rng}"] = costs["Cost"].where((costs["Age"] >= ages[0]) & (costs["Age"] < ages[1] + 1), other=0,)

    # ------------------------------------------------------------------------------------------------------------------
    # Compute the iteration-level results.
    results = {}

    results["lifespan"] = agents["death_age"].mean()
    results["lifespan_hiv"] = agents.loc[agents["got_hiv"], "death_age"].mean()
    results["lifespan_no_hiv"] = agents.loc[~agents["got_hiv"], "death_age"].mean()
    results["cost_total"] = costs["Cost"].sum()

    for e in Event:
        name = e.name.lower()
        results[f"cost_{name}"] = costs[f"cost_{name}"].sum()

    for ages in AGE_RANGES:
        rng = f"{ages[0]}_{ages[1]}"
        results[f"alive_{ages[0]}"] = agents[f"alive_{ages[0]}"].sum()
        results[f"cancers_{rng}"] = agents[f"cancer_{rng}"].sum()
        results[f"cancer_deaths_{rng}"] = agents[f"cancer_death_{rng}"].sum()
        results[f"cost_total_{rng}"] = costs[f"cost_{rng}"].sum()

    for field in ("cancers", "cancer_deaths", "cost_total"):
        results[f"{field}"] = results.pop(f"{field}_0_100")

    # ------------------------------------------------------------------------------------------------------------------
    # Cancer Incidence
    analysis = Analysis(scenario_dir, iteration)
    ci = 100_000 * analysis.incidence(CancerState.id, CancerState.LOCAL.value)
    cancer_age_groups = [15, 40, 45, 50, 55, 60]
    for i in range(len(cancer_age_groups) - 1):
        age_range = range(cancer_age_groups[i], cancer_age_groups[i + 1])
        value = round(ci.loc[age_range].mean(), 4)
        age_group = f"{cancer_age_groups[i]}_{cancer_age_groups[i + 1]}"
        results[f"Cancer_Inc_Per_100k_{age_group}"] = value

    # Save DataFrame
    pd.DataFrame(results, index=[0]).to_csv(iteration_path.joinpath("results.csv"), index=False)


def main(args):
    analyze(args.scenario_dir, args.iteration)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create analysis results for a single iteration")
    parser.add_argument("scenario_dir", help="directory containing the iteration output files")
    parser.add_argument("iteration", help="directory containing the iteration output files")
    args = parser.parse_args()

    main(args)
