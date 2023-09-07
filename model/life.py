import pickle

import numpy as np

from model.state import EventState, LifeState


class Life(EventState):
    def __init__(self, model):
        """ Life Status Tracker
            - Probability of dying is based on age and cancer status and should be updated:
                - Yearly (when the model changes the womens ages)
                - On cancer status event change
        """
        with open(model.transition_dir.joinpath("life_dictionary.pickle"), "rb") as openfile:
            life_dict = pickle.load(openfile)
        super().__init__(enum=LifeState, transition_dict=life_dict)

        self.model = model
        # Everyone starts out alive
        self.initiate(count=model.params.num_agents, state=LifeState.ALIVE, dtype=np.int8)
        self.living = self.values == LifeState.ALIVE

    def step(self):
        """ Simulate life change for all living agents.
            - Find the probability of death for each agent
            - Record a state change if they die
        """
        self.update_living()
        use_agents = self.model.unique_ids[self.living]
        probabilities = self.probabilities[use_agents]
        selected_agents = probabilities > self.model.rng.rand(len(probabilities))
        for unique_id in self.model.unique_ids[use_agents][selected_agents]:
            self.model.state_changes.record_event(
                (self.model.time, unique_id, LifeState.int, LifeState.ALIVE.value, LifeState.DEAD.value)
            )
            self.values[unique_id] = LifeState.DEAD.value

    def update_living(self):
        self.living = self.values == LifeState.ALIVE

    def update_probabilities(self):
        ages = [self.model.age] * self.model.params.num_agents
        hiv_state = self.model.hiv.values.astype(int)
        cancer_status = self.model.cancer.values.astype(int)
        self.probabilities = self.find_probabilities(keys=list(zip(ages, hiv_state, cancer_status)))
