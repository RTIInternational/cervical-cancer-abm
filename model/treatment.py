class CinTreatmentMethod:
    def __init__(self, name, params, rng):
        self.name = name
        self.params = params
        self.rng = rng

    def is_effective(self):
        return self.rng.random() < self.params.effectiveness


class CinTreatmentMethodFactory:
    def __init__(self, model):
        self.model = model
        self.params = model.params.treatment
        self.methods = [
            CinTreatmentMethod("leep", self.params.leep, self.model.rng),
            CinTreatmentMethod("cryo", self.params.cryo, self.model.rng),
        ]
        self.proportions = [m.params.proportion for m in self.methods]
        self.options = [i for i in range(len(self.methods))]

    def get_method(self):
        return self.model.rng.choice(self.options, p=self.proportions)
