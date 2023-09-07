import pickle

import numpy as np

from model.state import EventState, HivState


class Hiv(EventState):
    def __init__(self, model):
        with (open(model.transition_dir.joinpath("hiv_dictionary.pickle"), "rb")) as openfile:
            hiv_dict = pickle.load(openfile)
        super().__init__(enum=HivState, transition_dict=hiv_dict)
        """ HIV Status Tracker
            - Probability of HIV transition is based solely on age.
            - Probabilities should update yearly when the model changes a women's age
        """
        self.model = model
        # No one has HIV
        self.initiate(count=self.model.params.num_agents, state=HivState.NORMAL, dtype=np.int8)

    def step(self):
        """ Simulate HIV Transitions
            - Must be alive and not HIV infected
            - Record a transition for anyone with HIV
            - Determine if HIV is detected
        """
        if self.model.params.include_hiv:
            use_agents = self.model.unique_ids[self.model.life.living & (self.values == HivState.NORMAL)]
            probabilities = self.probabilities[use_agents]
            selected_agents = probabilities > self.model.rng.rand(len(probabilities))
            for unique_id in self.model.unique_ids[use_agents][selected_agents]:
                self.model.state_changes.record_event(
                    (self.model.time, unique_id, HivState.int, HivState.NORMAL.value, HivState.HIV.value)
                )
                self.values[unique_id] = HivState.HIV.value
                # --- HIV Detection
                if self.model.rng.rand() < self.model.params.hiv_detection_rate:
                    self.model.hiv_detected.add(unique_id)

                # ----- Update the agents HPV transition probabilities
                for strain in self.model.hpv_strains.values():
                    key = (
                        self.model.age,
                        strain.strain,
                        strain.hpv_immunity[unique_id],
                        strain.values[unique_id],
                        self.model.hiv.values[unique_id],
                    )
                    strain.probabilities[unique_id] = strain.transition_probability_dict[key]

                # ----- Update the agents life probability
                hiv = HivState.HIV.value
                canc = self.model.cancer.values[unique_id]
                self.model.life.probabilities[unique_id] = self.model.life.transition_dict[(self.model.age, hiv, canc)]

    def update_probabilities(self):
        if self.model.params.include_hiv:
            self.probabilities = self.find_probabilities(keys=[(self.model.age,)] * len(self.model.unique_ids))
