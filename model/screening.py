from enum import IntEnum, unique
from typing import Dict

from model.event import Event
from model.parameters import ScreeningParameters
from model.state import CancerState
from model.state import CancerDetectionState
from model.state import HpvState
from model.state import HpvStrain


@unique
class ScreeningTestResult(IntEnum):
    NEGATIVE = 0
    POSITIVE = 1
    CANCER = 2


@unique
class ScreeningState(IntEnum):
    ROUTINE = 1
    RE_TEST = 2
    SURVEILLANCE = 3


class ViaScreeningTest:
    def __init__(self, model):
        self.model = model
        self.params = model.params.screening.via

    def get_result(self, true_hpv_state: HpvState, true_cancer_state: CancerState) -> ScreeningTestResult:
        """ Return the screening test result given a woman's most advanced HPV state and her cancer state.

        Properties of the test:
        - If the HpvState is NORMAL, HPV, or CIN_1 and the test is specific, then return NEGATIVE.
        - If the HpvState is NORMAL, HPV, or CIN_1 and the test isn't specific, then return POSITIVE.
        - If the HpvState is CIN_2_3 and the test is sensitive, then return POSITIVE.
        - If the HpvState is CIN_2_3 and the test isn't sensitive, then return NEGATIVE.
        - If the HpvState is CANCER, the CancerState is LOCAL, and the test is sensitive, then return CANCER.
        - If the HpvState is CANCER, the CancerState is LOCAL, and the test isn't sensitive, then return NEGATIVE.
        - If the HpvState is CANCER and the CancerState is REGIONAL or DISTANT, then return CANCER
            (regardless of the sensitivity).

        Raise a ValueError if true_cancer_state is DEAD. Also raise a ValueError
        if true_hpv_state is CANCER and true_cancer_state is NORMAL.
        """

        if true_cancer_state == CancerState.DEAD:
            raise ValueError()
        elif true_hpv_state == HpvState.CANCER and true_cancer_state == CancerState.NORMAL:
            raise ValueError()
        elif true_hpv_state in [HpvState.NORMAL, HpvState.HPV, HpvState.CIN_1]:
            if self.model.rng.random() > self.params.specificity:
                return ScreeningTestResult.POSITIVE
            else:
                return ScreeningTestResult.NEGATIVE
        elif true_hpv_state == HpvState.CIN_2_3:
            if self.model.rng.random() < self.params.sensitivity:
                return ScreeningTestResult.POSITIVE
            else:
                return ScreeningTestResult.NEGATIVE
        elif true_cancer_state == CancerState.LOCAL:
            if self.model.rng.random() < self.params.sensitivity:
                return ScreeningTestResult.CANCER
            else:
                return ScreeningTestResult.NEGATIVE
        else:
            return ScreeningTestResult.CANCER


class DnaScreeningTest:
    def __init__(self, model):
        self.model = model
        self.params = model.params.screening.dna

    def get_result(self, true_hpv_states: Dict[HpvStrain, HpvState]) -> Dict[HpvStrain, ScreeningTestResult]:
        """ Return the screening test result given a woman's true HPV state for each
            strain. An independent result is provided for each strain.

        Properties of the test:
        - Detectable HPV strains are SIXTEEN, EIGHTEEN, and HIGH_RISK.
        - We say that a woman "has a strain" when her state for that strain is
          one of HPV, CIN_1, CIN_2_3, or CANCER.
        - Always return NEGATIVE for undetectable strains.
        - If the woman has a detectable strain of HPV and the test is sensitive, then
          return POSITIVE for each detectable strain that she has.
        - If the woman has a detectable strain of HPV and the test isn't sensitive,
          then return NEGATIVE for all strains.
        - If the woman doesn't have a detectable strain of HPV and the test is
          specific, then return NEGATIVE for all strains.
        - If the woman doesn't have a detectable strain of HPV and the test isn't
          specific, then return POSITIVE for the HIGH_RISK strain and NEGATIVE for
          other strains.
        """

        detectable = [
            HpvStrain.SIXTEEN,
            HpvStrain.EIGHTEEN,
            HpvStrain.HIGH_RISK,
        ]

        # Step 1: Compute an overall positive/negative result using the test sensitivity and specificity.

        false_positive = False

        if all(true_hpv_states[strain] == HpvState.NORMAL for strain in detectable):
            if self.model.rng.random() > self.params.specificity:
                overall_result = ScreeningTestResult.POSITIVE
                false_positive = True
            else:
                overall_result = ScreeningTestResult.NEGATIVE
        else:
            if self.model.rng.random() < self.params.sensitivity:
                overall_result = ScreeningTestResult.POSITIVE
            else:
                overall_result = ScreeningTestResult.NEGATIVE

        if overall_result == ScreeningTestResult.NEGATIVE:
            return {strain: ScreeningTestResult.NEGATIVE for strain in HpvStrain}

        # Step 2: Compute strain-specific results using deterministic rules.

        result = {strain: ScreeningTestResult.NEGATIVE for strain in HpvStrain}

        for strain in detectable:
            if true_hpv_states[strain] != HpvState.NORMAL:
                result[strain] = ScreeningTestResult.POSITIVE

        if false_positive:
            result[HpvStrain.HIGH_RISK] = ScreeningTestResult.POSITIVE

        return result


class CancerInspectionScreeningTest:
    def __init__(self, model):
        self.model = model
        self.params = model.params.screening.cancer_inspection

    def get_result(self, true_cancer_state: CancerState) -> ScreeningTestResult:
        """ Return the screening test result given a woman's true cancer state.

        Properties of the test:
        - Detectable cancer states are REGIONAL and DISTANT.
        - If the woman has a detectable state and the test is sensitive, then return CANCER.
        - If the woman has a detectable state and the test isn't sensitive, then return NEGATIVE.
        - If the woman doesn't have a detectable state and the test is specific, then return NEGATIVE.
        - If the woman doesn't have a detectable state and the test isn't specific, then return CANCER.

        Raise a ValueError if true_cancer_state is DEAD.
        """

        if true_cancer_state == CancerState.DEAD:
            raise ValueError()
        elif true_cancer_state in [CancerState.NORMAL, CancerState.LOCAL]:
            if self.model.rng.random() > self.params.specificity:
                return ScreeningTestResult.CANCER
            else:
                return ScreeningTestResult.NEGATIVE
        else:
            if self.model.rng.random() < self.params.sensitivity:
                return ScreeningTestResult.CANCER
            else:
                return ScreeningTestResult.NEGATIVE


def is_due_for_screening(model, unique_id):
    """ Return True if the woman is due for a screening test based on her current screening state,
        her screening history, and the screening interval guidelines.

    Requirements:
    - Women who have been diagnosed with cancer are no longer screened.
    - Women in the ROUTINE screening state aren't screened if they are younger or older than threshold ages.
    - Women who have been screened within the past N years aren't due to be screened again,
        where N is an interval that varies by screening state.
    - Women with HIV have a different screening interval.
        This interval will be used in place of her state-based interval if the HIV-specific interval is shorter.
    """

    if model.cancer_detection.values[unique_id] == CancerDetectionState.DETECTED:
        return False

    t1 = model.age < model.params.screening.age_routine_start
    t2 = model.age > model.params.screening.age_routine_end
    if model.screening_state.values[unique_id] == ScreeningState.ROUTINE and (t1 or t2):
        return False

    if model.screening_state.values[unique_id] == ScreeningState.ROUTINE:
        interval = model.params.screening.interval_routine
    elif model.screening_state.values[unique_id] == ScreeningState.RE_TEST:
        interval = model.params.screening.interval_re_test
    elif model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE:
        interval = model.params.screening.interval_surveillance
    else:
        raise NotImplementedError(f"Unexpected screening state: {model.screening_state.values[unique_id]}")

    if unique_id in model.hiv_detected:
        interval = min(interval, model.params.screening.interval_hiv)
    if unique_id not in model.dicts.last_screen_age:
        return True
    if model.age - model.dicts.last_screen_age.get(unique_id, 0) >= interval:
        return True
    return False


def is_compliant_with_screening(model, unique_id):
    if model.screening_state.values[unique_id] == ScreeningState.ROUTINE:
        return model.compliant_routine_state.values[unique_id]
    elif model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE:
        return model.compliant_surveillance_state.values[unique_id]
    return True


class ScreeningProtocol:
    def __init__(
        self,
        model,
        params: ScreeningParameters,
        via_screening_test: ViaScreeningTest,
        dna_screening_test: DnaScreeningTest,
        cancer_inspection_screening_test: CancerInspectionScreeningTest,
    ):
        self.params = params
        self.dna_screening_test = dna_screening_test
        self.via_screening_test = via_screening_test
        self.cancer_inspection_screening_test = cancer_inspection_screening_test
        self.model = model

    def apply(self):
        raise NotImplementedError("Must implement this method in a subclass")

    def get_via_result(self, unique_id):
        return self.via_screening_test.get_result(
            true_hpv_state=self.model.max_hpv_state.values[unique_id],
            true_cancer_state=self.model.cancer.values[unique_id],
        )

    def get_dna_result(self, unique_id):
        return self.dna_screening_test.get_result(
            true_hpv_states={strain: self.model.hpv_strains[strain].values[unique_id] for strain in HpvStrain}
        )

    def get_cancer_inspection_result(self, unique_id):
        return self.cancer_inspection_screening_test.get_result(true_cancer_state=self.model.cancer.values[unique_id],)


class NoScreeningProtocol(ScreeningProtocol):
    def __init__(self, *args, **kwargs):
        pass

    def is_due(self, *args, **kwargs):
        return False

    def apply(self, *args, **kwargs):
        pass


class ViaScreeningProtocol(ScreeningProtocol):
    def apply(self, unique_id=None):
        unique_ids = [unique_id]
        if unique_id is None:
            unique_ids = self.model.unique_ids[self.model.life.living]
        for unique_id in unique_ids:
            if not is_due_for_screening(self.model, unique_id):
                continue
            if not is_compliant_with_screening(self.model, unique_id):
                continue
            self.model.dicts.last_screen_age[unique_id] = self.model.age

            if self.model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE:
                event = Event.SURVEILLANCE_VIA
            else:
                event = Event.SCREENING_VIA

            self.model.events.record_event((self.model.time, unique_id, event.value, self.params.via.cost))

            result = self.get_via_result(unique_id)

            if result == ScreeningTestResult.NEGATIVE:
                self.model.screening_state.values[unique_id] = ScreeningState.ROUTINE
            elif result == ScreeningTestResult.POSITIVE:
                self.model.treat_cin(unique_id)
                self.model.screening_state.values[unique_id] = ScreeningState.SURVEILLANCE
            elif result == ScreeningTestResult.CANCER:
                self.model.detect_cancer(unique_id)
                self.model.screening_state.values[unique_id] = ScreeningState.SURVEILLANCE
            else:
                raise NotImplementedError(f"Unexpected screening test result: {result}")


class DnaThenTreatmentScreeningProtocol(ScreeningProtocol):
    def apply(self, unique_id=None):
        unique_ids = [unique_id]
        if unique_id is None:
            unique_ids = self.model.unique_ids[self.model.life.living]
        for unique_id in unique_ids:
            if not is_due_for_screening(self.model, unique_id):
                continue
            if not is_compliant_with_screening(self.model, unique_id):
                continue

            self.model.dicts.last_screen_age[unique_id] = self.model.age

            if self.model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE:
                event = Event.SURVEILLANCE_DNA
            else:
                event = Event.SCREENING_DNA
            self.model.events.record_event((self.model.time, unique_id, event.value, self.params.dna.cost))

            result = self.get_dna_result(unique_id)

            if all(result[strain] == ScreeningTestResult.NEGATIVE for strain in HpvStrain):
                self.model.screening_state.values[unique_id] = ScreeningState.ROUTINE
            else:
                if self.model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE:
                    event2 = Event.SURVEILLANCE_CANCER_INSPECTION
                else:
                    event2 = Event.SCREENING_CANCER_INSPECTION

                self.model.events.record_event(
                    (self.model.time, unique_id, event2.value, self.params.cancer_inspection.cost)
                )

                result = self.get_cancer_inspection_result(unique_id)

                if result == ScreeningTestResult.NEGATIVE:
                    self.model.treat_cin(unique_id)
                    self.model.screening_state.values[unique_id] = ScreeningState.SURVEILLANCE
                elif result == ScreeningTestResult.CANCER:
                    self.model.detect_cancer(unique_id)
                    self.model.screening_state.values[unique_id] = ScreeningState.SURVEILLANCE
                else:
                    raise NotImplementedError(f"Unexpected screening test result: {result}")


class DnaThenViaScreeningProtocol(ScreeningProtocol):
    def apply(self, unique_id=None):
        unique_ids = [unique_id]
        if unique_id is None:
            unique_ids = self.model.unique_ids[self.model.life.living]

        for unique_id in unique_ids:
            if not is_due_for_screening(self.model, unique_id):
                continue
            if not is_compliant_with_screening(self.model, unique_id):
                continue

            self.model.dicts.last_screen_age[unique_id] = self.model.age

            if self.model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE:
                event = Event.SURVEILLANCE_DNA
            else:
                event = Event.SCREENING_DNA

            self.model.events.record_event((self.model.time, unique_id, event.value, self.params.dna.cost))
            result = self.get_dna_result(unique_id)

            stp_pos = ScreeningTestResult.POSITIVE
            if all(result[strain] == ScreeningTestResult.NEGATIVE for strain in HpvStrain):
                self.model.screening_state.values[unique_id] = ScreeningState.ROUTINE
            elif (result[HpvStrain.SIXTEEN] == stp_pos) or (result[HpvStrain.EIGHTEEN] == stp_pos):

                if self.model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE:
                    event2 = Event.SURVEILLANCE_CANCER_INSPECTION
                else:
                    event2 = Event.SCREENING_CANCER_INSPECTION

                self.model.events.record_event(
                    (self.model.time, unique_id, event2.value, self.params.cancer_inspection.cost)
                )
                result = self.get_cancer_inspection_result(unique_id)

                if result == ScreeningTestResult.NEGATIVE:
                    self.model.treat_cin(unique_id)
                    self.model.screening_state.values[unique_id] = ScreeningState.SURVEILLANCE
                elif result == ScreeningTestResult.CANCER:
                    self.model.detect_cancer(unique_id)
                    self.model.screening_state.values[unique_id] = ScreeningState.SURVEILLANCE
                else:
                    raise NotImplementedError(f"Unexpected screening test result: {result}")
            else:
                if self.model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE:
                    event2 = Event.SURVEILLANCE_VIA
                else:
                    event2 = Event.SCREENING_VIA

                self.model.events.record_event((self.model.time, unique_id, event2.value, self.params.via.cost))
                result = self.get_via_result(unique_id)

                if result == ScreeningTestResult.NEGATIVE:
                    self.model.screening_state.values[unique_id] = ScreeningState.RE_TEST
                elif result == ScreeningTestResult.POSITIVE:
                    self.model.treat_cin(unique_id)
                    self.model.screening_state.values[unique_id] = ScreeningState.SURVEILLANCE
                elif result == ScreeningTestResult.CANCER:
                    self.model.detect_cancer(unique_id)
                    self.model.screening_state.values[unique_id] = ScreeningState.SURVEILLANCE
                else:
                    raise NotImplementedError(f"Unexpected screening test result: {result}")


class DnaThenTriageScreeningProtocol(ScreeningProtocol):
    def apply(self, unique_id=None):
        unique_ids = [unique_id]
        if unique_id is None:
            unique_ids = self.model.unique_ids[self.model.life.living]

        for unique_id in unique_ids:
            if not is_due_for_screening(self.model, unique_id):
                continue
            if not is_compliant_with_screening(self.model, unique_id):
                continue

            self.model.dicts.last_screen_age[unique_id] = self.model.age

            if self.model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE:
                event = Event.SURVEILLANCE_DNA
            else:
                event = Event.SCREENING_DNA

            self.model.events.record_event((self.model.time, unique_id, event.value, self.params.dna.cost))
            result = self.get_dna_result(unique_id)

            stp_pos = ScreeningTestResult.POSITIVE
            if all(result[strain] == ScreeningTestResult.NEGATIVE for strain in HpvStrain):
                self.model.screening_state.values[unique_id] = ScreeningState.ROUTINE
            elif (result[HpvStrain.SIXTEEN] == stp_pos) or (result[HpvStrain.EIGHTEEN] == stp_pos):

                if self.model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE:
                    event2 = Event.SURVEILLANCE_CANCER_INSPECTION
                else:
                    event2 = Event.SCREENING_CANCER_INSPECTION
                self.model.events.record_event(
                    (self.model.time, unique_id, event2.value, self.params.cancer_inspection.cost)
                )
                result = self.get_cancer_inspection_result(unique_id)

                if result == ScreeningTestResult.NEGATIVE:
                    self.model.treat_cin(unique_id)
                    self.model.screening_state.values[unique_id] = ScreeningState.SURVEILLANCE
                elif result == ScreeningTestResult.CANCER:
                    self.model.detect_cancer(unique_id)
                    self.model.screening_state.values[unique_id] = ScreeningState.SURVEILLANCE
                else:
                    raise NotImplementedError(f"Unexpected screening test result: {result}")
            else:
                self.model.screening_state.values[unique_id] = ScreeningState.RE_TEST


protocols = {
    "none": NoScreeningProtocol,
    "via": ViaScreeningProtocol,
    "dna_then_treatment": DnaThenTreatmentScreeningProtocol,
    "dna_then_via": DnaThenViaScreeningProtocol,
    "dna_then_triage": DnaThenTriageScreeningProtocol,
}
