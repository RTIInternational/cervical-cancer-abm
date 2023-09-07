import pickle
from collections import defaultdict
from copy import copy

import numpy as np

from model.misc_functions import filter_hpv_dict, normalize, random_selection
from model.state import CancerState, EventState, HpvImmunity, HpvState, HpvStrain


class Hpv(EventState):
    def __init__(self, model, strain):
        with (open(model.transition_dir.joinpath("hpv_dictionary.pickle"), "rb")) as openfile:
            hpv_dict = pickle.load(openfile)
            strain_dict = filter_hpv_dict(hpv_dict, strain)
        super().__init__(enum=HpvState, transition_dict=strain_dict)
        """ HPV State Tracker
            - Probability of HPV transition is based on: age, strain, immunity, current strain status, and hiv status
            - Probability should update:
                - Yearly (when the model changes the womens ages)
                - When a women's current strain status changes (occurs within this class)
                - When a women's HIV status changes (occurs within the HIV class)
        """
        self.model = model
        self.strain = strain
        self.transition_probability_dict = self.make_transition_probabilities()
        self.probabilities = np.zeros(1)
        self.agents_with_cancer = set()

    def step(self):
        """ Simulate HPV transitions for each strain: Must be alive and cannot have cancer
        Those who do not have cancer are subject to transition.
        """
        normal_status = self.model.cancer.values == CancerState.NORMAL
        unique_ids = self.model.unique_ids[self.model.life.living & normal_status]
        probabilities = self.probabilities[unique_ids]
        selected_agents = unique_ids[probabilities > self.model.rng.rand(len(probabilities))]

        # ----- Force a transition
        for unique_id in selected_agents:
            # --- Find the current status and make a change
            current_state = self.values[unique_id]
            hiv_status = self.model.hiv.values[unique_id]
            key = (
                self.model.age,
                self.strain,
                self.hpv_immunity[unique_id],
                self.values[unique_id],
                hiv_status,
            )
            probs_list = copy(self.transition_dict[key])
            # --- Remove their current states probability
            probs_list[current_state - 1] = 0
            cdf = normalize(probs_list, return_cdf=True)

            new = random_selection(random=self.model.rng.rand(), cdf=cdf, options=self.integers)

            self.model.state_changes.record_event(
                (self.model.time, unique_id, HpvStrain(self.strain).int, self.values[unique_id], HpvState(new).value)
            )
            self.values[unique_id] = HpvState(new).value

            # ----- Returning to normal builds some immunity to HPV
            if new == HpvState.NORMAL:
                self.hpv_immunity[unique_id] = max(self.hpv_immunity[unique_id], HpvImmunity.NATURAL.value)
            # --- Cancer: record state change and update probability
            elif new == HpvState.CANCER:
                # Only move to cancer if agent does not already have cancer
                if unique_id not in self.agents_with_cancer:
                    self.agents_with_cancer.add(unique_id)
                    # state change
                    self.model.state_changes.record_event(
                        (self.model.time, unique_id, CancerState.int, CancerState.NORMAL.value, CancerState.LOCAL.value)
                    )
                    # cancer progression probability
                    key = (self.model.cancer_detection.values[unique_id], CancerState.LOCAL.value)
                    self.model.cancer.probabilities[unique_id] = self.model.cancer.transition_probability_dict[key]
                    # cancer status change
                    self.model.cancer.values[unique_id] = CancerState.LOCAL.value
                    hiv = self.model.hiv.values[unique_id]
                    self.model.life.probabilities[unique_id] = self.model.life.transition_dict[
                        (self.model.age, hiv, CancerState.LOCAL.value)
                    ]

            # ----- Update the transition_probabilities
            key = (
                self.model.age,
                self.strain,
                self.hpv_immunity[unique_id],
                self.values[unique_id],
                hiv_status,
            )
            self.probabilities[unique_id] = self.transition_probability_dict[key]

    def make_transition_probabilities(self):
        """ Create a dictionary of probabilities to transition (excluding the current state)
        """
        probs = dict()
        for k, v in self.transition_dict.items():
            state = k[3]
            probability_to_transition = 1 - v[state - 1]
            probs[k] = probability_to_transition
        return probs

    def update_probabilities(self):
        """ Loop up each agents transition probability. Occurs once a year
        """
        keys = list(
            zip(
                [self.model.age] * len(self.model.unique_ids),
                [self.strain] * len(self.model.unique_ids),
                self.hpv_immunity.astype(int),
                self.values.astype(int),
                self.model.hiv.values.astype(int),
            )
        )
        self.probabilities = np.zeros(len(self.model.unique_ids))

        locs = defaultdict(list)
        for i, key in enumerate(keys):
            locs[key].append(i)

        for key, value in locs.items():
            self.probabilities[value] = self.transition_probability_dict[key]

    def update_hpv_state(self):
        self.model.max_hpv_state.values = np.vstack([[self.model.hpv_strains[s.value].values] for s in HpvStrain]).max(
            axis=0
        )
