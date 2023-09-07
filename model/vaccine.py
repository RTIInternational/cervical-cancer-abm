import numpy as np


class VaccinationProtocol:
    def __init__(self, model):
        self.model = model
        self.params = model.params.vaccination

    def apply(self):
        # ----- Check vacination schedule:
        if self.model.age in self.params.schedule:
            p = self.params.schedule[self.model.age]
            unique_ids = self.model.unique_ids[self.model.life.living]
            selected_agents = np.array([p] * len(unique_ids)) > self.model.rng.rand(len(unique_ids))

            for unique_id in unique_ids[selected_agents]:
                self.model.vaccinate(unique_id)
