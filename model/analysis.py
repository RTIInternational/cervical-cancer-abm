import pandas as pd
import numpy as np
from pathlib import Path
from model.parameters import Parameters
from model.state import HpvState, HpvStrain, HivState, CancerState, CancerDetectionState, LifeState


class Analysis:
    """
    Provide some common analysis routines for the model's output data.

    Many of the methods accept parameters named `field` or `states`. A field comes in two varieties:
       - the ID of a State, such as `HpvState.id`
       - a new field computed within this class

    Available states are the values that may be found in a field. They are defined differently depending on which
    variety of field they belong to:
       - For a state field, the states are simply the states in that statechart. This class operates on the
        numeric value of these states, even though they are actually Python `enum`s. When passing values to
         the `states` parameters, you should therefore pass the enum value, such as `HpvState.CIN_1.value`.
      - For a computed field, the states are defined on a case-by-case basis.

    """

    def __init__(self, scenario_dir: str, iteration: int, add_computed_fields: bool = False):
        """ Create a model analysis object from the model's input and output files.
        """

        self.scenario_dir = Path(scenario_dir)
        self.iteration_dir = self.scenario_dir.joinpath(f"iteration_{iteration}")
        self.params = Parameters()
        self.params.update_from_file(self.scenario_dir.joinpath("parameters.yml"))

        # ----- We'll use the same indexes for multiple series and data frames - create them once to conserve resources
        self.time_index = pd.Index(range(self.params.num_steps + 1))
        ia = self.params.initial_age
        self.age_index = pd.Index(range(ia, int(self.params.num_steps / self.params.steps_per_year + 1) + ia))
        self.agent_index = pd.Index(range(self.params.num_agents))
        self.agent_age_index = pd.MultiIndex.from_product(
            [self.agent_index, self.age_index], names=["Unique_ID", "Age"],
        )

        # ----- Use model output to make event dataframes/timelines for each statechart + additional computed fields.
        self.chart_ids = [HivState.id, CancerState.id, CancerDetectionState.id, LifeState.id]
        self.chart_ids = self.chart_ids + [HpvStrain(strain).name for strain in HpvStrain]

        self.agent_events = {}
        agent_timelines = {}

        self.state_events = pd.read_parquet(self.iteration_dir.joinpath("state_changes.parquet"))

        for chart_id in self.chart_ids:
            self.agent_events[chart_id] = (
                self.state_events[self.state_events.State == chart_id]
                .set_index(["Unique_ID", "Time"])
                .drop(["State"], axis=1)
            )
            agent_timelines[chart_id] = self.create_timeline_from_events(self.agent_events[chart_id])

        self.agent_timeline = pd.DataFrame(agent_timelines)

        if add_computed_fields:
            self._add_computed_timelines()

        # Set up a cache for some of the more resource-intensive computations that we may need more than once.
        # Example: the number of people who are alive at each time step is used in prevalence and incidence rates
        self.cache_count_in = {}
        self.cache_count_new = {}

    def create_timeline_from_events(self, events: pd.DataFrame) -> pd.Series:
        """ A timeline series contains one element per agent and time step, where every time step is represented.
            It provides the agent's state at each time step.
        """
        events.reset_index(inplace=True)
        events["Age"] = round(events["Time"] / self.params.steps_per_year, 0) + self.params.initial_age
        events["Age"] = events["Age"].astype(int)
        e_indexed = events.set_index(["Unique_ID", "Age"])

        # If there are multiple transitions for an index, go from 1 to 3, or 2 to 4. Instead of 1 to 2, and 2 to 3
        e_no_dups = e_indexed.loc[~e_indexed.index.duplicated(keep="last")]

        timeline = e_no_dups[["To"]].rename(columns={"To": "state"}).reindex(self.agent_age_index)["state"]
        # At the initial age: All start at the base state (1).
        timeline[(timeline.index.get_level_values("Age") == self.params.initial_age) & np.isnan(timeline.values)] = 1
        # Fill NAs with value above until reaching next valid value
        timeline = timeline.fillna(method="ffill").astype("category")

        return timeline

    def prevalence(self, field: str, states: tuple, filter_dict: dict = dict(), alive_only: bool = True):
        """ Return a series containing the prevalence rate for the given states. The prevalence rate at a given time
        step is defined as the proportion of the living population who are in one of the states at that time step.
        """
        if alive_only:
            filter_dict[LifeState.id] = (LifeState.ALIVE.value,)
        num = self.count_in(field, states, filter_dict)
        denum = self.count_in(LifeState.id, (LifeState.ALIVE.value,), filter_dict)

        return num / denum

    def incidence(self, field: str, states: tuple, filter_dict: dict = dict(), alive_only: bool = True):
        """ Return a series containing the incidence rate for the given states. The incidence rate at a given time
        step is defined as the proportion of the living population who entered one of the states during that time step.
        """
        if alive_only:
            filter_dict[LifeState.id] = (LifeState.ALIVE.value,)
        num = self.count_new(field, states, filter_dict)
        denum = self.fix_alive_count(self.count_in(LifeState.id, (LifeState.ALIVE.value,), filter_dict))

        return num / denum

    def count_in(self, field: str, states: tuple, filter_dict: dict = None):
        """ Return a series containing the number of agents who are in one of the given states at each time step.
        """
        df = self.agent_timeline

        if filter_dict:
            for i in filter_dict.keys():
                target_states = filter_dict[i] if isinstance(filter_dict[i], tuple) else (filter_dict[i],)
                df = df[df[i].isin(target_states)]

        target_states = states if isinstance(states, tuple) else (states,)
        try:
            return self.cache_count_in[(field, target_states, str(filter_dict))]
        except KeyError:
            count = df[df[field].isin(target_states)].groupby(level="Age").size().reindex(self.age_index).fillna(0)
            self.cache_count_in[(field, target_states, str(filter_dict))] = count

            return count

    def count_new(self, field: str, states: tuple, filter_dict: dict = None):
        """ Return a series containing the number of agents who entered one of the given states at each time step.
        """
        df = self.agent_timeline
        if isinstance(filter_dict, dict):
            for i in filter_dict.keys():
                target_states = filter_dict[i] if isinstance(filter_dict[i], tuple) else (filter_dict[i],)
                df = df[df[i].isin(target_states)]

        target_states = states if isinstance(states, tuple) else (states,)

        try:
            return self.cache_count_new[(field, target_states, str(filter_dict))]
        except KeyError:
            events = self.agent_events[field]
            events = events.set_index(["Unique_ID", "Age"])
            indices = set([item for item in df.index.values])
            events_idx = set(events.index.values)
            use_indices = indices.intersection(events_idx)
            events = events.loc[list(use_indices)]

            count = (
                events[events["To"].isin(target_states)].groupby(level="Age").size().reindex(self.age_index).fillna(0)
            )
            self.cache_count_new[(field, target_states, str(filter_dict))] = count

            return count

    def _add_computed_timelines(self):
        """ Compute timelines for additional fields that aren't output directly by the model.

        The computed fields and their states are:

            hpv_max - Most advanced state among all the HPV statecharts.

            hpv_16_18_high - Whether the most advanced HPV state is HpvState.HPV and that state occurs in the HPV
            statechart for strains 16, 18, or Other High Risk. Available states are True and False.

            cin_1 - Whether the most advanced HPV state is HpvState.CIN_1. Available states are True and False.

            cin_2_3 - Whether the most advanced HPV state is HpvState.CIN_2_3. Available states are True and False.
        """
        self.agent_timeline["hpv_max"] = (
            self.agent_timeline[[HpvStrain(strain).name for strain in HpvStrain]].max(axis=1).astype("category")
        )

        test1 = self.agent_timeline["hpv_max"] == HpvState.HPV.value
        test2 = (
            (self.agent_timeline[HpvStrain.SIXTEEN.name] == HpvState.HPV.value)
            | (self.agent_timeline[HpvStrain.EIGHTEEN.name] == HpvState.HPV.value)
            | (self.agent_timeline[HpvStrain.HIGH_RISK.name] == HpvState.HPV.value)
        )

        self.agent_timeline["hpv_16_18_high"] = test1 & test2

        self.agent_timeline["cin_1"] = self.agent_timeline["hpv_max"] == HpvState.CIN_1.value

        self.agent_timeline["cin_2_3"] = self.agent_timeline["hpv_max"] == HpvState.CIN_2_3.value

    def fix_alive_count(self, count_alive):
        alive_count = count_alive.rolling(2).mean()
        alive_count[self.params.initial_age] = count_alive[self.params.initial_age]

        return alive_count
