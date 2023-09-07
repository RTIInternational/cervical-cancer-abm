from pathlib import Path
import yaml


class ParameterContainer:
    def __init__(self):
        self.keys = set()

    def add_param(self, key, value):
        self.keys.add(key)
        setattr(self, key, value)

    def update_from_dict(self, params):
        """
        Update the parameter values using values found in a dictionary.
        """

        for key in params:
            if key in self.keys:
                if isinstance(getattr(self, key), ParameterContainer):
                    getattr(self, key).update_from_dict(params[key])
                else:
                    setattr(self, key, params[key])
            else:
                raise AttributeError(f"Key {key} has not been defined as a parameter")

    def update_from_file(self, params_file):
        """
        Update the parameter values using values found in a file. The file must be in YAML format.
        """

        params_file = Path(params_file)

        params = {}
        if params_file.exists():
            with params_file.open(mode="r") as f:
                params = yaml.safe_load(f)  # safe_load() returns None if the file is empty.
            if params is None:
                params = {}
        else:
            print("Warning: Input directory does not contain parameter file.")

        self.update_from_dict(params)

    def export_to_dict(self):
        """
        Export the parameter values to a Python dictionary.
        """

        out = {}
        for key in self.keys:
            if isinstance(getattr(self, key), ParameterContainer):
                out[key] = getattr(self, key).export_to_dict()
            else:
                out[key] = getattr(self, key)

        return out

    def export_to_file(self, params_file):
        """
        Export the parameters values to a YAML file.
        """
        with Path(params_file).open(mode="w") as f:
            yaml.dump(self.export_to_dict(), f, default_flow_style=False)


class Parameters(ParameterContainer):
    def __init__(self):
        super().__init__()

        self.add_param("num_agents", 100)
        self.add_param("num_steps", 120)
        self.add_param("steps_per_year", 12)
        self.add_param("initial_age", 9)
        self.add_param("seed", 1111)
        self.add_param("hiv_detection_rate", 1)
        self.add_param("include_hiv", True)

        self.add_param("vaccination", VaccinationParameters())
        self.add_param("screening", ScreeningParameters())
        self.add_param("treatment", TreatmentParameters())


class ScreeningParameters(ParameterContainer):
    def __init__(self):
        super().__init__()
        self.add_param("protocol", "none")
        self.add_param("age_routine_start", 25)
        self.add_param("age_routine_end", 49)
        self.add_param("interval_routine", 3)
        self.add_param("interval_re_test", 1)
        self.add_param("interval_surveillance", 1)
        self.add_param("interval_hiv", 3)

        self.add_param("via", ScreeningTestParameters())
        self.via.sensitivity = 0.73
        self.via.specificity = 0.67
        self.via.cost = 2.52

        self.add_param("dna", ScreeningTestParameters())
        self.dna.sensitivity = 0.88
        self.dna.specificity = 0.60
        self.dna.cost = 18.00

        self.add_param("cancer_inspection", ScreeningTestParameters())
        self.cancer_inspection.sensitivity = 1.00
        self.cancer_inspection.specificity = 1.00
        self.cancer_inspection.cost = 2.52

        self.add_param("compliance", ComplianceParameters())


class ScreeningTestParameters(ParameterContainer):
    def __init__(self):
        super().__init__()
        self.add_param("cost", 0)
        self.add_param("sensitivity", 1)
        self.add_param("specificity", 1)


class ComplianceParameters(ParameterContainer):
    def __init__(self):
        super().__init__()
        self.add_param("never", 0)
        self.add_param("never_surveillance", 0)


class TreatmentParameters(ParameterContainer):
    def __init__(self):
        super().__init__()

        self.add_param("leep", CinTreatmentMethodParameters())
        self.leep.effectiveness = 0.94
        self.leep.proportion = 0.15
        self.leep.cost = 32.00

        self.add_param("cryo", CinTreatmentMethodParameters())
        self.cryo.effectiveness = 0.88
        self.cryo.proportion = 0.85
        self.cryo.cost = 1.52

        self.add_param("cancer_cost_local", 1186)
        self.add_param("cancer_cost_regional", 1389)
        self.add_param("cancer_cost_distant", 1146)


class CinTreatmentMethodParameters(ParameterContainer):
    def __init__(self):
        super().__init__()
        self.add_param("cost", 0)
        self.add_param("effectiveness", 1)
        self.add_param("proportion", 0)


class VaccinationParameters(ParameterContainer):
    def __init__(self):
        super().__init__()

        self.add_param("cost", 15.00)
        self.add_param("schedule", {})
