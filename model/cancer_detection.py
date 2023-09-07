import pickle

import numpy as np

from model.event import Event
from model.state import CancerDetectionState, CancerState, EventState, TimeSinceCancerDetectionState


class CancerDetection(EventState):
    def __init__(self, model):
        with (open(model.transition_dir.joinpath("cancer_detection_dictionary.pickle"), "rb")) as openfile:
            cancer_detection_dict = pickle.load(openfile)
        super().__init__(enum=CancerDetectionState, transition_dict=cancer_detection_dict)
        self.model = model
        # No one can be deteced yet
        self.initiate(count=self.model.params.num_agents, state=CancerDetectionState.UNDETECTED, dtype=np.int8)
        self.probabilities = np.zeros(self.model.params.num_agents)

    def step(self):
        """ Simulate NORMAL Cancer Detection: Must be alive, undetected, and have cancer
        Note: cancer.step() is responsible for updating the cancer_detection probabilities
        """
        undetected = self.values == CancerDetectionState.UNDETECTED
        non_normal_status = self.model.cancer.values != CancerState.NORMAL

        use_agents = self.model.unique_ids[self.model.life.living & undetected & non_normal_status]
        probabilities = self.probabilities[use_agents]
        selected_agents = probabilities > self.model.rng.rand(len(probabilities))

        from_v = CancerDetectionState.UNDETECTED.value
        to_v = CancerDetectionState.DETECTED.value
        for unique_id in self.model.unique_ids[use_agents][selected_agents]:
            self.model.state_changes.record_event((self.model.time, unique_id, CancerDetectionState.int, from_v, to_v))
            self.values[unique_id] = CancerDetectionState.DETECTED.value
            # ----- Treat cancer and update dictionaries
            self.treat_cancer(unique_id)
            self.model.dicts.cancer_detection_time[unique_id] = self.model.time
            self.model.dicts.time_since_cancer_detection[unique_id] = TimeSinceCancerDetectionState.WITHIN_5_YEARS.value

    def treat_cancer(self, unique_id: int):
        """ Other than the cost, the model doesn't explicitly implement anything related to cancer treatment.
        """
        state = self.model.cancer.values[unique_id]
        if state == CancerState.LOCAL:
            cost = self.model.params.treatment.cancer_cost_local
        elif state == CancerState.REGIONAL:
            cost = self.model.params.treatment.cancer_cost_regional
        elif state == CancerState.DISTANT:
            cost = self.model.params.treatment.cancer_cost_distant
        else:
            raise NotImplementedError("Unexpected cancer state {}".format(state))

        self.model.events.record_event((self.model.time, unique_id, Event.TREATMENT_CANCER.value, cost))
