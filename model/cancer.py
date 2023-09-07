import pickle as pickle

import numpy as np

from model.misc_functions import normalize, random_selection
from model.state import CancerDetectionState, CancerState, EventState, LifeState, TimeSinceCancerDetectionState


class Cancer(EventState):
    def __init__(self, model):
        with (open(model.transition_dir.joinpath("cancer_dictionary.pickle"), "rb")) as openfile:
            cancer_dict = pickle.load(openfile)
        super().__init__(enum=CancerState, transition_dict=cancer_dict)
        """ Cancer Status Tracker
            - Probability of NORMAL -> LOCAL transition is handled within the HPV class
            - Probability of further cancer progression is based on cancer detection and cancer states.
            - Probabilities are updated if:
                - Cancer detection status changes (handled in the cancer detection state)
                - Cancer progression status changes (handled in this class)
        """
        self.model = model
        self.transition_probability_dict = self.make_transition_probabilities()
        self.probabilities = np.zeros(0)
        # Everyone starts out cancer free
        self.initiate(count=self.model.params.num_agents, state=CancerState.NORMAL, dtype=np.int8)

    def step(self):
        """ Simulate progression through the cancer states: Must be living, be LOCAL or REGIONAL, and not be detected
            Note: Transition from Normal to Cancer is handled elsewhere
        """
        non_normal_status = np.isin(self.values, [CancerState.LOCAL, CancerState.REGIONAL])
        not_detected = self.model.cancer_detection.values == CancerDetectionState.UNDETECTED
        unique_ids = self.model.unique_ids[self.model.life.living & non_normal_status & not_detected]

        probabilities = self.probabilities[unique_ids]
        selected_agents = unique_ids[probabilities > self.model.rng.rand(len(probabilities))]

        # ----- Force a transition
        for unique_id in selected_agents:
            key = (self.model.cancer_detection.values[unique_id], self.values[unique_id])

            current_state = self.values[unique_id]
            key = (self.model.cancer_detection.values[unique_id], current_state)
            probs_list = self.transition_dict[key]
            # --- Remove their current states probability
            probs_list[current_state - 1] = 0
            cdf = normalize(probs_list, return_cdf=True)
            new = random_selection(self.model.rng.rand(), cdf, self.integers)

            self.model.state_changes.record_event(
                (self.model.time, unique_id, CancerState.int, self.values[unique_id], new)
            )
            self.values[unique_id] = new

            # ----- Update Cancer detection probability and cancer transition probability
            self.model.cancer_detection.probabilities[unique_id] = self.model.cancer_detection.transition_dict[new]
            key = (self.model.cancer_detection.values[unique_id], new)
            self.probabilities[unique_id] = self.transition_probability_dict[key]

            # ----- Update death probabilities
            hiv_state = self.model.hiv.values[unique_id]
            self.model.life.probabilities[unique_id] = self.model.life.transition_dict[(self.model.age, hiv_state, new)]

            # --- If agent dies:
            if new == CancerState.DEAD:
                self.model.state_changes.record_event(
                    (self.model.time, unique_id, LifeState.int, LifeState.ALIVE.value, LifeState.DEAD.value)
                )
                self.model.life.values[unique_id] = LifeState.DEAD.value

        # ----- Update Cancer Detection
        for unique_id, v in self.model.dicts.time_since_cancer_detection.items():
            if v == TimeSinceCancerDetectionState.WITHIN_5_YEARS:
                if self.model.compute_years_since(self.model.dicts.cancer_detection_time[unique_id]) > 5:
                    self.model.dicts.time_since_cancer_detection[
                        unique_id
                    ] = TimeSinceCancerDetectionState.BEYOND_5_YEARS.value

    def make_transition_probabilities(self):
        """ Create a dictionary of probabilities to transition (excluding the current state)
        """
        probs = dict()
        for k, v in self.transition_dict.items():
            state = k[1]
            probability_to_transition = 1 - v[state - 1]
            probs[k] = probability_to_transition
        return probs

    def initiate_probabilities(self):
        """ Loop up each agents transition probability.
        """
        keys = list(zip(self.model.cancer_detection.values, self.values))
        self.probabilities = np.zeros(len(keys))
        for unique_id, key in enumerate(keys):
            self.probabilities[unique_id] = self.transition_probability_dict[key]
