import numpy as np

from enum import Enum
from pathlib import Path
from tqdm import trange

from model.event import Event
from model.logger import LoggerFactory
from model.parameters import Parameters
from model.vaccine import VaccinationProtocol
from model.misc_functions import EventStorage
from model.treatment import CinTreatmentMethodFactory
from model.screening import ScreeningState, DnaScreeningTest, ViaScreeningTest, CancerInspectionScreeningTest, protocols
from model.state import HpvState, HpvStrain, CancerDetectionState, HpvImmunity, Empty, int_map

from model.cancer_detection import CancerDetection
from model.cancer import Cancer
from model.life import Life
from model.hiv import Hiv
from model.hpv import Hpv


class CervicalModel:
    def __init__(self, scenario_dir: Path, iteration: int = 0, logger: LoggerFactory = None, seed: int = 1111):
        """Create a new CervicalModel simulator.

        Args:
            scenario_dir (Path): Directory containing the model's input files.
            iteration (int, optional): [description]. Defaults to 0.
            logger (LoggerFactory, optional): Logger to use for writing log messages. Defaults to None.
            seed (int, optional): [description]. Defaults to 1111.
        """

        # ----- Setup the class structure
        self.scenario_dir = scenario_dir
        self.iteration_dir = self.scenario_dir.joinpath(f"iteration_{iteration}")
        self.iteration_dir.mkdir(exist_ok=True)
        # Use the iteration specific transition dictionaries if they exists
        self.transition_dir = self.scenario_dir.joinpath("transition_dictionaries")
        if self.iteration_dir.joinpath("transition_dictionaries").exists():
            self.transition_dir = self.iteration_dir.joinpath("transition_dictionaries")
        self.params = Parameters()
        self.params.update_from_file(self.scenario_dir.joinpath("parameters.yml"))
        self.time = 0
        self.rng = np.random.RandomState(seed)
        self.logger = logger
        self.logger.info("Random seed: {}".format(seed))
        self.logger.info("Model parameters: \n{}".format(self.params))

        # ----- Setup the storage containers
        self.state_changes = EventStorage(column_names=["Time", "Unique_ID", "State_ID", "From", "To"])
        self.events = EventStorage(column_names=["Time", "Unique_ID", "Event", "Cost"])
        # --- Dictionaries
        self.dicts = Empty("Collection of Dictionaries")
        self.dicts.cancer_detection_time = dict()
        self.dicts.time_since_cancer_detection = dict()
        self.dicts.cin_treatment_methods = dict()
        self.dicts.last_screen_age = dict()
        # --- Sets
        self.hiv_detected = set()
        self.hpv_vaccinations = set()

        # ----- Setup the model states
        self.life = Life(model=self)
        self.hiv = Hiv(model=self)
        self.cancer_detection = CancerDetection(model=self)
        self.cancer = Cancer(model=self)
        # --- HPV State: One for every strain
        self.hpv_strains = dict()
        for strain in [item.value for item in HpvStrain]:
            self.hpv_strains[strain] = Hpv(model=self, strain=strain)

        # ----- Now that States are in place, load the agents
        self.load_agents()

        # ----- Setup the protocols
        self.cin_treatment_method_factory = CinTreatmentMethodFactory(model=self)
        self.via_screening_test = ViaScreeningTest(model=self)
        self.dna_screening_test = DnaScreeningTest(model=self)
        self.cancer_inspection_screening_test = CancerInspectionScreeningTest(model=self)
        ScreeningProtocolClass = protocols[self.params.screening.protocol]
        self.screening_protocol = ScreeningProtocolClass(
            model=self,
            params=self.params.screening,
            via_screening_test=self.via_screening_test,
            dna_screening_test=self.dna_screening_test,
            cancer_inspection_screening_test=self.cancer_inspection_screening_test,
        )
        self.vaccination_protocol = VaccinationProtocol(model=self)

    def run(self, print_status=False):
        # Run the model
        run_range = range(self.params.num_steps)
        if print_status:
            run_range = trange(self.params.num_steps, desc="---> Running model")
        for _ in run_range:
            self.step()
        self.save_output()

    def save_output(self):
        # Save the output
        df = self.state_changes.make_events()
        df["State"] = df["State_ID"].map(int_map)
        location1 = self.iteration_dir.joinpath("state_changes.parquet")
        df.drop("State_ID", axis=1).to_parquet(location1, index=False)
        location2 = self.iteration_dir.joinpath("events.parquet")
        self.events.make_events().to_parquet(location2, index=False)

    def step(self):
        if self.time % self.params.steps_per_year == 0:
            self.yearly_update()
        # ----- Order: Hpv (by strain), Hiv, Cancer Progression, Cancer Detection, Life
        self.life.update_living()
        self.step_hpv()
        self.step_hiv()
        self.step_cancer()
        self.step_cancer_detection()
        self.step_life()
        self.time += 1

    def step_hpv(self):
        self.hpv_strains[HpvStrain.LOW_RISK].step()
        self.hpv_strains[HpvStrain.HIGH_RISK].step()
        self.hpv_strains[HpvStrain.SIXTEEN].step()
        self.hpv_strains[HpvStrain.EIGHTEEN].step()
        self.hpv_strains[max(HpvStrain)].update_hpv_state()

    def step_hiv(self):
        self.hiv.step()

    def step_cancer(self):
        self.cancer.step()

    def step_cancer_detection(self):
        self.cancer_detection.step()

    def step_life(self):
        self.life.step()

    def load_agents(self):
        """ Add the agents to the model based on parameter inputs
        Order matters here, as some states rely on otherss
        """
        num_agents = self.params.num_agents
        self.age = self.params.initial_age
        self.unique_ids = np.array([item for item in range(num_agents)])

        self.cancer.initiate_probabilities()

        for hpv in self.hpv_strains.values():
            hpv.initiate(count=num_agents, state=HpvState.NORMAL, dtype=np.int8)
            hpv.hpv_immunity = self.initiate_array(count=num_agents, state=HpvImmunity.NORMAL, dtype=np.int8)
            hpv.update_probabilities()

        # - Only required to call this for one strain - as it finds the max of all strains
        self.max_hpv_state = Empty("max_hpv_state")
        self.hpv_strains[max(HpvStrain)].update_hpv_state()

        self.life.update_probabilities()
        self.hiv.update_probabilities()

        # ----- Additional Intervention States
        self.screening_state = Empty("screening")
        self.screening_state.values = self.initiate_array(count=num_agents, state=ScreeningState.ROUTINE, dtype=np.int8)
        self.compliant_routine_state = Empty("compliant_routine")
        self.compliant_routine_state.values = np.array(
            self.rng.rand(num_agents) >= self.params.screening.compliance.never
        )
        self.compliant_surveillance_state = Empty("compliant_surveillance")
        self.compliant_surveillance_state.values = np.array(
            self.rng.rand(num_agents) >= self.params.screening.compliance.never_surveillance
        )

    def initiate_array(self, count: int, state: Enum, dtype: type = np.int8) -> np.array:
        array = np.zeros(count, dtype=dtype)
        array.fill(state.value)
        return array

    def yearly_update(self):
        if self.time != 0:
            self.age += 1
        # ----- Life, HIV, and HPV probabilities are based on age
        self.life.update_probabilities()
        self.hiv.update_probabilities()
        for strain in self.hpv_strains:
            self.hpv_strains[strain].update_probabilities()
        # ------ Apply screening and vaccination protocols
        self.screening_protocol.apply()
        self.vaccination_protocol.apply()

    # ------ Additional Functions --------------------------------------------------------------------------------------
    def vaccinate(self, unique_id: int):
        self.events.record_event((self.time, unique_id, Event.VACCINATION.value, self.params.vaccination.cost))
        self.hpv_vaccinations.add(unique_id)
        for item in self.hpv_strains:
            if HpvStrain(item).name != HpvStrain.LOW_RISK.name:
                strain = self.hpv_strains[item]
                strain.hpv_immunity[unique_id] = HpvImmunity.VACCINE.value
                # Update transition probability
                key = (
                    self.age,
                    item,
                    strain.hpv_immunity[unique_id],
                    strain.values[unique_id],
                    self.hiv.values[unique_id],
                )
                strain.probabilities[unique_id] = strain.transition_probability_dict[key]

    def treat_cin(self, unique_id: int):
        if unique_id not in self.dicts.cin_treatment_methods:
            self.dicts.cin_treatment_methods[unique_id] = self.cin_treatment_method_factory.get_method()

        method = self.cin_treatment_method_factory.methods[self.dicts.cin_treatment_methods[unique_id]]

        events = {
            "leep": Event.TREATMENT_LEEP,
            "cryo": Event.TREATMENT_CRYO,
        }

        self.events.record_event((self.time, unique_id, events[method.name].value, method.params.cost))
        # ----- If treatment is effective, all strains return to normal
        if method.is_effective():
            for strain in self.hpv_strains:
                if self.hpv_strains[strain].values[unique_id] != HpvState.NORMAL:
                    self.state_changes.record_event(
                        (
                            self.time,
                            unique_id,
                            HpvStrain(strain).int,
                            self.hpv_strains[strain].values[unique_id],
                            HpvState.NORMAL,
                        )
                    )
                    self.hpv_strains[strain].values[unique_id] = HpvState.NORMAL.value

    def detect_cancer(self, unique_id: int):
        """ During a screening, an agents cancer was detected. Record this and update the agents value.
        """
        state_int = CancerDetectionState.int
        # Record state change
        self.state_changes.record_event(
            (self.time, unique_id, state_int, self.cancer_detection.values[unique_id], CancerDetectionState.DETECTED)
        )
        # Update value
        self.cancer_detection.values[unique_id] = CancerDetectionState.DETECTED.value

    def compute_years_since(self, time: int) -> float:
        """ Return the number of years since the given time step. Partial years are represented by floats.
        """
        return (self.time - time) / self.params.steps_per_year
