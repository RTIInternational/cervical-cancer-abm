import pytest
from model.event import Event
from model.screening import (
    DnaThenTreatmentScreeningProtocol,
    DnaThenTriageScreeningProtocol,
    DnaThenViaScreeningProtocol,
    NoScreeningProtocol,
    ScreeningState,
    ScreeningTestResult,
    ViaScreeningProtocol,
    is_compliant_with_screening,
    is_due_for_screening,
)
from model.state import CancerDetectionState, CancerState, HivState, HpvState, HpvStrain

from model.tests.fixtures import model_screening


def test_screening(model_screening):
    # Make sure all the base parameters are in line:
    params = model_screening.params.screening
    assert params.age_routine_start == 25
    assert params.age_routine_end == 49
    assert params.interval_routine == 3
    assert params.interval_re_test == 1
    assert params.interval_surveillance == 1
    assert params.interval_hiv == 2
    assert params.via.cost == 2.52
    assert params.dna.cost == 18
    assert params.cancer_inspection.cost == 2.52


def default_model(
    model,
    age=9,
    screening_state=ScreeningState.ROUTINE,
    last_screen_age=None,
    compliant_routine=True,
    compliant_surveillance=True,
    cancer_detection=CancerDetectionState.UNDETECTED,
    cancer_state=CancerState.NORMAL,
    hiv_detected=False,
    hiv_state=HivState.NORMAL,
    hpv_state=HpvState.NORMAL,
):
    unique_id = 0
    model.params.screening.age_routine_start = 20
    model.params.screening.age_routine_end = 50
    model.params.screening.via.cost = 2
    model.params.screening.interval_re_test = 5
    model.params.screening.interval_surveillance = 3
    model.params.screening.interval_routine = 10
    model.age = age
    model.screening_state.values[unique_id] = screening_state
    model.dicts.last_screen_age.pop(unique_id, None)
    if last_screen_age:
        model.dicts.last_screen_age[unique_id] = last_screen_age
    model.compliant_routine_state.values[unique_id] = compliant_routine
    model.compliant_surveillance_state.values[unique_id] = compliant_surveillance
    model.cancer_detection.values[unique_id] = cancer_detection
    model.cancer.values[unique_id] = cancer_state
    model.hiv.values[unique_id] = hiv_state
    if hiv_detected:
        model.hiv_detected.add(unique_id)

    for strain in model.hpv_strains:
        model.hpv_strains[strain].values[unique_id] = hpv_state
    return model


unique_id = 0


@pytest.fixture
def negative_dna_result():
    return {strain: ScreeningTestResult.NEGATIVE for strain in HpvStrain}


@pytest.fixture(params=[HpvStrain.SIXTEEN, HpvStrain.EIGHTEEN, HpvStrain.HIGH_RISK])
def positive_dna_result(request):
    result = {strain: ScreeningTestResult.NEGATIVE for strain in HpvStrain}
    result[request.param] = ScreeningTestResult.POSITIVE
    return result


@pytest.fixture(params=[HpvStrain.SIXTEEN, HpvStrain.EIGHTEEN])
def positive_16_18_dna_result(request):
    result = {strain: ScreeningTestResult.NEGATIVE for strain in HpvStrain}
    result[request.param] = ScreeningTestResult.POSITIVE
    return result


@pytest.fixture
def positive_other_high_dna_result(request):
    result = {strain: ScreeningTestResult.NEGATIVE for strain in HpvStrain}
    result[HpvStrain.HIGH_RISK] = ScreeningTestResult.POSITIVE
    return result


class MockScreeningTest:
    def __init__(self, result=ScreeningTestResult.NEGATIVE):
        self.result = result

    def get_result(self, *args, **kwargs):
        return self.result


class TestIsDue:
    # Check if women is due for screening
    def test_cancer(self, model_screening):
        # Women diagnosed with cancer will not be screened even if they are otherwise due
        model = default_model(
            model_screening,
            age=25,
            screening_state=ScreeningState.ROUTINE,
            cancer_state=CancerState.LOCAL,
            cancer_detection=CancerDetectionState.DETECTED,
        )
        assert is_due_for_screening(model, 0) is False

    @pytest.mark.parametrize(
        "age, last_screen_age, due",
        [
            (19, None, False),
            (20, None, True),
            (20, 11, False),
            (30, 20, True),
            (30, 21, False),
            (50, None, True),
            (51, None, False),
        ],
    )
    def test_routine(self, model_screening, age, last_screen_age, due):
        """
        Women in the ROUTINE state will screened if they haven't been screened recently,
        but only if they're within the appropriate age range.
        """
        model = default_model(
            model_screening, age=age, screening_state=ScreeningState.ROUTINE, last_screen_age=last_screen_age
        )
        assert is_due_for_screening(model, 0) == due

    @pytest.mark.parametrize(
        "age, last_screen_age, due",
        [
            (19, None, True),
            (20, None, True),
            (20, 16, False),
            (30, 25, True),
            (30, 26, False),
            (50, None, True),
            (51, None, True),
        ],
    )
    def test_re_test(self, model_screening, age, last_screen_age, due):
        """
        Women in the RE_TEST state will be screened if they haven't been screened recently. The age range doesn't apply.
        """
        model = default_model(
            model_screening, age=age, screening_state=ScreeningState.RE_TEST, last_screen_age=last_screen_age
        )

        assert is_due_for_screening(model, 0) == due

    @pytest.mark.parametrize(
        "age,last_screen_age,due",
        [
            (19, None, True),
            (20, None, True),
            (20, 18, False),
            (30, 27, True),
            (30, 28, False),
            (50, None, True),
            (51, None, True),
        ],
    )
    def test_surveillance(self, model_screening, age, last_screen_age, due):
        """
        Women in the SURVEILLANCE state will screened if they haven't been screened recently. Age range doesn't apply.
        """
        model = default_model(
            model_screening, age=age, screening_state=ScreeningState.SURVEILLANCE, last_screen_age=last_screen_age
        )

        assert is_due_for_screening(model, 0) == due

    @pytest.mark.parametrize(
        "screening_state, last_screen_age, interval_hiv, due",
        [
            (ScreeningState.ROUTINE, 26, 1, True),
            (ScreeningState.ROUTINE, 26, 20, False),
            (ScreeningState.RE_TEST, 31, 1, True),
            (ScreeningState.RE_TEST, 31, 20, False),
            (ScreeningState.SURVEILLANCE, 33, 1, True),
            (ScreeningState.SURVEILLANCE, 33, 20, False),
        ],
    )
    def test_hiv(self, model_screening, screening_state, last_screen_age, interval_hiv, due):
        """
        The acceptable screening interval may be different for women with HIV. It should be the minimum of the
        HIV-specific interval and the usual interval associated with their screening state.
        """
        model = default_model(
            model_screening, age=35, screening_state=screening_state, last_screen_age=last_screen_age, hiv_detected=True
        )
        model.params.screening.interval_hiv = interval_hiv

        assert is_due_for_screening(model_screening, 0) == due


class TestIsCompliant:
    @pytest.mark.parametrize("compliant", [True, False])
    def test_routine(self, model_screening, compliant):
        """ Women in the ROUTINE state are compliant based on the value of their `compliant_routine` parameter.
        """
        model = default_model(model_screening, compliant_routine=compliant)
        assert is_compliant_with_screening(model, 0) == compliant

    def test_re_test(self, model_screening):
        """ Women in the RE_TEST state are always compliant.
        """
        model = default_model(model_screening, screening_state=ScreeningState.RE_TEST)
        assert is_compliant_with_screening(model, 0)

    @pytest.mark.parametrize("compliant", [True, False])
    def test_surveillance(self, model_screening, compliant):
        """ Women in the SURVEILLANCE state are compliant based on the value of their `compliant_routine` parameter.
        """
        model = default_model(
            model_screening, screening_state=ScreeningState.SURVEILLANCE, compliant_surveillance=compliant
        )
        assert is_compliant_with_screening(model, 0) == compliant


class TestNoScreeningProtocol:
    @pytest.mark.parametrize(
        "screening_state", [ScreeningState.ROUTINE, ScreeningState.RE_TEST, ScreeningState.SURVEILLANCE]
    )
    def test_no_screening(self, model_screening, screening_state):
        """
        Women assigned to the NoScreening protocol are never screened, even if they are eligible based on their age.
        """
        model = default_model(model_screening, age=20, screening_state=screening_state)

        protocol = NoScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(),
        )

        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == screening_state
        assert model.dicts.last_screen_age.get(unique_id, 0) == 0
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        assert model.events.arr.size == 0


@pytest.mark.parametrize(
    "ProtocolClass",
    [
        ViaScreeningProtocol,
        DnaThenTreatmentScreeningProtocol,
        DnaThenTriageScreeningProtocol,
        DnaThenViaScreeningProtocol,
    ],
)
class TestProtocolNoncompliant:
    def test_routine(self, model_screening, ProtocolClass):
        """
        Women in the ROUTINE state are never screened when they are noncompliant with routine screening.
        """
        model = default_model(model_screening, age=20, screening_state=ScreeningState.ROUTINE, compliant_routine=False)

        protocol = ProtocolClass(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )

        protocol.apply(unique_id)

        assert model_screening.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model_screening.dicts.last_screen_age.get(unique_id, 0) == 0
        assert model_screening.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        assert model_screening.events.arr.size == 0

    def test_surveillance(self, model_screening, ProtocolClass):
        """
        Women in the SURVEILLANCE state are never screened when they are noncompliant with surveillance screening.
        """
        model = default_model(
            model=model_screening,
            age=40,
            last_screen_age=20,
            screening_state=ScreeningState.SURVEILLANCE,
            compliant_surveillance=False,
        )

        protocol = ProtocolClass(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )

        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        assert model.events.arr.size == 0


class TestViaScreeningProtocol:
    @pytest.mark.parametrize("age", [15, 55])
    def test_routine_age_limit(self, model_screening, age):
        """
        Women in the ROUTINE state will not be screened if they are outside the appropriate age range.
        """
        model = default_model(model_screening, age=age, screening_state=ScreeningState.ROUTINE)

        protocol = ViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 0
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        assert model.events.arr.size == 0

    def test_routine_via_negative(self, model_screening):
        """
        Women in the ROUTINE state will return to the ROUTINE state after a negative VIA test result.
        """
        model = default_model(model_screening, age=20, screening_state=ScreeningState.ROUTINE)

        protocol = ViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.NEGATIVE,),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events["Event"].values[0] == Event.SCREENING_VIA.value
        assert events["Cost"].values[0] == model.params.screening.via.cost

    def test_routine_via_positive(self, model_screening):
        """
        Women in the ROUTINE state will be treated and move to the SURVEILLANCE state after a positive VIA test.
        """
        model = default_model(model_screening, age=20, screening_state=ScreeningState.ROUTINE)

        protocol = ViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.POSITIVE,),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 2
        assert events["Event"].values[0] == Event.SCREENING_VIA.value
        assert events["Cost"].values[0] == model_screening.params.screening.via.cost

    def test_routine_via_cancer(self, model_screening):
        """
        Women in the ROUTINE state will have their cancer detected and move
        to the SURVEILLANCE state after a cancer VIA test result.
        """
        model = default_model(model_screening, age=20, screening_state=ScreeningState.ROUTINE)

        protocol = ViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.CANCER,),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.DETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events["Event"].values[0] == Event.SCREENING_VIA.value
        assert events["Cost"].values[0] == model_screening.params.screening.via.cost

    @pytest.mark.parametrize("age", [15, 55])
    def test_surveillance_age_limit(self, model_screening, age):
        """
        Women in the SURVEILLANCE state will be screened even if they are outside the appropriate age range.
        """
        model = default_model(model_screening, age=age, screening_state=ScreeningState.SURVEILLANCE)

        protocol = ViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == age
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events["Event"].values[0] == Event.SURVEILLANCE_VIA.value
        assert events["Cost"].values[0] == model_screening.params.screening.via.cost

    def test_surveillance_via_negative(self, model_screening):
        """
        Women in the SURVEILLANCE state will move to the ROUTINE state after a negative VIA test result.
        """
        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = ViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.NEGATIVE,),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events["Event"].values[0] == Event.SURVEILLANCE_VIA.value
        assert events["Cost"].values[0] == model_screening.params.screening.via.cost

    def test_surveillance_via_positive(self, model_screening):
        """
        Women in the SURVEILLANCE state will be treated and stay in the SURVEILLANCE state after a positive VIA test.
        """
        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = ViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.POSITIVE,),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 2
        assert events["Event"].values[0] == Event.SURVEILLANCE_VIA.value
        assert events["Cost"].values[0] == model.params.screening.via.cost

    def test_surveillance_via_cancer(self, model_screening):
        """
        Women in the SURVEILLANCE state will have their cancer detected and stay in the
        SURVEILLANCE state after a cancer VIA test result.
        """
        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = ViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.CANCER,),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.DETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events["Event"].values[0] == Event.SURVEILLANCE_VIA.value
        assert events["Cost"].values[0] == model.params.screening.via.cost


class TestDnaThenTreatmentScreeningProtocol:
    @pytest.mark.parametrize("age", [15, 55])
    def test_routine_age_limit(self, model_screening, age):
        """
        Women in the ROUTINE state will not be screened if they are outside the
        appropriate age range.
        """
        model = default_model(model_screening, age=age, screening_state=ScreeningState.ROUTINE)

        protocol = DnaThenTreatmentScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 0
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        assert model.events.make_events().shape[0] == 0

    def test_routine_dna_negative(self, model_screening, negative_dna_result):
        """
        Women in the ROUTINE state will return to the ROUTINE state after a negative DNA test result.
        """

        model = default_model(model_screening, age=20, screening_state=ScreeningState.ROUTINE)

        protocol = DnaThenTreatmentScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=negative_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    def test_routine_dna_positive_cancer_negative(self, model_screening, positive_dna_result):
        """
        Women in the ROUTINE state will be treated and move to the SURVEILLANCE state after a positive
        DNA test result followed by a negative cancer inspection result.
        """

        model = default_model(model_screening, age=20, screening_state=ScreeningState.ROUTINE)

        protocol = DnaThenTreatmentScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.NEGATIVE,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 3
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SCREENING_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost

    def test_routine_dna_positive_cancer_positive(self, model_screening, positive_dna_result):
        """
        Women in the ROUTINE state will have their cancer detected and move to the SURVEILLANCE state after a
        positive DNA test result followed by a positive cancer inspection result.
        """

        model = default_model(model_screening, age=20, screening_state=ScreeningState.ROUTINE)

        protocol = DnaThenTreatmentScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.CANCER,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.DETECTED
        events = model.events.make_events()
        assert events.shape[0] == 2
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SCREENING_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost

    @pytest.mark.parametrize("age", [15, 55])
    def test_surveillance_age_limit(self, model_screening, age, negative_dna_result):
        """
        Women in the SURVEILLANCE state will be screened even if they are outside the appropriate age range.
        """

        model = default_model(model_screening, age=age, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenTreatmentScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=negative_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == age
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    def test_surveillance_dna_negative(self, model_screening, negative_dna_result):
        """
        Women in the SURVEILLANCE state will move to the ROUTINE state after a negative DNA test result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenTreatmentScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=negative_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    def test_surveillance_dna_positive_cancer_negative(self, model_screening, positive_dna_result):
        """
        Women in the SURVEILLANCE state will be treated and stay in the SURVEILLANCE
        state after a positive DNA test result followed by a negative cancer inspection result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenTreatmentScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.NEGATIVE,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 3
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SURVEILLANCE_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost

    def test_surveillance_dna_positive_cancer_positive(self, model_screening, positive_dna_result):
        """
        Women in the SURVEILLANCE state will have their cancer detected and stay in the SURVEILLANCE state after a
        positive DNA test result followed by a positive cancer inspection result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenTreatmentScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.CANCER,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.DETECTED
        events = model.events.make_events()
        assert events.shape[0] == 2
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SURVEILLANCE_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost


class TestDnaThenTriageScreeningProtocol:
    @pytest.mark.parametrize("age", [15, 55])
    def test_routine_age_limit(self, model_screening, age):
        """
        Women in the ROUTINE state will not be screened if they are outside the
        appropriate age range.
        """

        model = default_model(model_screening, age=age, screening_state=ScreeningState.ROUTINE)

        protocol = DnaThenTriageScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 0
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        assert len(model.events.make_events()) == 0

    @pytest.mark.parametrize("age", [15, 55])
    def test_retest_age_limit(self, model_screening, age, negative_dna_result):
        """
        Women in the RE_TEST state will be screened even if they are outside the appropriate age range.
        """

        model = default_model(model_screening, age=age, screening_state=ScreeningState.RE_TEST)

        protocol = DnaThenTriageScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=negative_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == age
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    @pytest.mark.parametrize("screening_state", [ScreeningState.ROUTINE, ScreeningState.RE_TEST])
    def test_routine_dna_negative(self, model_screening, negative_dna_result, screening_state):
        """
        Women in the ROUTINE or RE_TEST state will move to the ROUTINE state after a negative DNA test result.
        """

        model = default_model(model_screening, age=20, screening_state=screening_state)

        protocol = DnaThenTriageScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=negative_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    @pytest.mark.parametrize("screening_state", [ScreeningState.ROUTINE, ScreeningState.RE_TEST])
    def test_routine_dna_positive_16_18_cancer_negative(
        self, model_screening, positive_16_18_dna_result, screening_state
    ):
        """
        Women in the ROUTINE or RE_TEST state will be treated and move to the SURVEILLANCE state after a positive
        DNA test result for strain 16 or 18 followed by a negative cancer inspection result.
        """

        model = default_model(model_screening, age=20, screening_state=screening_state)

        protocol = DnaThenTriageScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_16_18_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.NEGATIVE,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 3
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SCREENING_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost

    @pytest.mark.parametrize("screening_state", [ScreeningState.ROUTINE, ScreeningState.RE_TEST])
    def test_routine_dna_positive_16_18_cancer_positive(
        self, model_screening, positive_16_18_dna_result, screening_state
    ):
        """
        Women in the ROUTINE or RE_TEST state will have their cancer detected and move to the SURVEILLANCE state after
        a positive DNA test result for strain 16 or 18 followed by a positive cancer inspection result.
        """

        model = default_model(model_screening, age=20, screening_state=screening_state)

        protocol = DnaThenTriageScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_16_18_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.CANCER,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.DETECTED
        events = model.events.make_events()
        assert events.shape[0] == 2
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SCREENING_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost

    @pytest.mark.parametrize("screening_state", [ScreeningState.ROUTINE, ScreeningState.RE_TEST])
    def test_routine_dna_positive_other_high(self, model_screening, positive_other_high_dna_result, screening_state):
        """
        Women in the ROUTINE or RE_TEST state will move to the RE_TEST state after a
        positive DNA test result for a high risk strain other than 16 or 18.
        """

        model = default_model(model_screening, age=20, screening_state=screening_state)

        protocol = DnaThenTriageScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_other_high_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.RE_TEST
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    @pytest.mark.parametrize("age", [15, 55])
    def test_surveillance_age_limit(self, model_screening, age, negative_dna_result):
        """
        Women in the SURVEILLANCE state will be screened even if they are outside the appropriate age range.
        """

        model = default_model(model_screening, age=age, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenTriageScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=negative_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == age
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    def test_surveillance_dna_negative(self, model_screening, negative_dna_result):
        """
        Women in the SURVEILLANCE state will move to the ROUTINE state after a negative DNA test result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenTriageScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=negative_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    def test_surveillance_dna_positive_16_18_cancer_negative(self, model_screening, positive_16_18_dna_result):
        """
        Women in the SURVEILLANCE state will be treated and stay in the SURVEILLANCE
        state after a positive DNA test result for strain 16 or 18 followed by a
        negative cancer inspection result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenTriageScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_16_18_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.NEGATIVE,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 3
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SURVEILLANCE_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost

    def test_surveillance_dna_positive_16_18_cancer_positive(self, model_screening, positive_16_18_dna_result):
        """
        Women in the SURVEILLANCE state will have their cancer detected and stay in the SURVEILLANCE state after a
        positive DNA test result for strain 16 or 18 followed by a positive cancer inspection result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenTriageScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_16_18_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.CANCER,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.DETECTED
        events = model.events.make_events()
        assert events.shape[0] == 2
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SURVEILLANCE_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost

    def test_surveillance_dna_positive_other_high(self, model_screening, positive_other_high_dna_result):
        """
        Women in the SURVEILLANCE state will move to the RE_TEST state after a
        positive DNA test result for a high risk strain other than 16 or 18.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenTriageScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_other_high_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.RE_TEST
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost


class TestDnaThenViaScreeningProtocol:
    @pytest.mark.parametrize("age", [15, 55])
    def test_routine_age_limit(self, model_screening, age):
        """
        Women in the ROUTINE state will not be screened if they are outside the appropriate age range.
        """

        model = default_model(model_screening, age=age, screening_state=ScreeningState.ROUTINE)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 0
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        assert len(model.events.make_events()) == 0

    @pytest.mark.parametrize("age", [15, 55])
    def test_retest_age_limit(self, model_screening, age, negative_dna_result):
        """
        Women in the RE_TEST state will be screened even if they are outside the appropriate age range.
        """

        model = default_model(model_screening, age=age, screening_state=ScreeningState.RE_TEST)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=negative_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == age
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    @pytest.mark.parametrize("screening_state", [ScreeningState.ROUTINE, ScreeningState.RE_TEST])
    def test_routine_dna_negative(self, model_screening, negative_dna_result, screening_state):
        """
        Women in the ROUTINE or RE_TEST state will move to the ROUTINE state after a negative DNA test result.
        """

        model = default_model(model_screening, age=20, screening_state=screening_state)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=negative_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    @pytest.mark.parametrize("screening_state", [ScreeningState.ROUTINE, ScreeningState.RE_TEST])
    def test_routine_dna_positive_16_18_cancer_negative(
        self, model_screening, positive_16_18_dna_result, screening_state
    ):
        """
        Women in the ROUTINE or RE_TEST state will be treated and move to the SURVEILLANCE state after a positive
        DNA test result for strain 16 or 18 followed by a negative cancer inspection result.
        """

        model = default_model(model_screening, age=20, screening_state=screening_state)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_16_18_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.NEGATIVE,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 3
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SCREENING_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost

    @pytest.mark.parametrize("screening_state", [ScreeningState.ROUTINE, ScreeningState.RE_TEST])
    def test_routine_dna_positive_16_18_cancer_positive(
        self, model_screening, positive_16_18_dna_result, screening_state
    ):
        """
        Women in the ROUTINE or RE_TEST state will have their cancer detected and move to the SURVEILLANCE state after
        a positive DNA test result for strain 16 or 18 followed by a positive cancer inspection result.
        """

        model = default_model(model_screening, age=20, screening_state=screening_state)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_16_18_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.CANCER,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.DETECTED
        events = model.events.make_events()
        assert events.shape[0] == 2
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SCREENING_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost

    @pytest.mark.parametrize("screening_state", [ScreeningState.ROUTINE, ScreeningState.RE_TEST])
    def test_routine_dna_positive_other_high_via_negative(
        self, model_screening, positive_other_high_dna_result, screening_state
    ):
        """
        Women in the ROUTINE or RE_TEST state will move to the RE_TEST state after a positive DNA test result for a
        high risk strain other than 16 or 18 followed by a negative VIA test result.
        """

        model = default_model(model_screening, age=20, screening_state=screening_state)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.NEGATIVE,),
            dna_screening_test=MockScreeningTest(result=positive_other_high_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.RE_TEST
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 2
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SCREENING_VIA.value
        assert events.Cost.values[1] == model.params.screening.via.cost

    @pytest.mark.parametrize("screening_state", [ScreeningState.ROUTINE, ScreeningState.RE_TEST])
    def test_routine_dna_positive_other_high_via_positive(
        self, model_screening, positive_other_high_dna_result, screening_state
    ):
        """
        Women in the ROUTINE or RE_TEST state will be treated and move to the SURVEILLANCE state after a positive DNA
        test result for a high risk strain other than 16 or 18 followed by a positive VIA test result.
        """

        model = default_model(model_screening, age=20, screening_state=screening_state)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.POSITIVE,),
            dna_screening_test=MockScreeningTest(result=positive_other_high_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 3
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SCREENING_VIA.value
        assert events.Cost.values[1] == model.params.screening.via.cost

    @pytest.mark.parametrize("screening_state", [ScreeningState.ROUTINE, ScreeningState.RE_TEST])
    def test_routine_dna_positive_other_high_via_cancer(
        self, model_screening, positive_other_high_dna_result, screening_state
    ):
        """
        Women in the ROUTINE or RE_TEST state will have their cancer detected and move to the SURVEILLANCE state after
        a positive DNA test result for a high risk strain other than 16 or 18 followed by a cancer VIA test result.
        """

        model = default_model(model_screening, age=20, screening_state=screening_state)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.CANCER,),
            dna_screening_test=MockScreeningTest(result=positive_other_high_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 20
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.DETECTED
        events = model.events.make_events()
        assert events.shape[0] == 2
        assert events.Event.values[0] == Event.SCREENING_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SCREENING_VIA.value
        assert events.Cost.values[1] == model.params.screening.via.cost

    @pytest.mark.parametrize("age", [15, 55])
    def test_surveillance_age_limit(self, model_screening, age, negative_dna_result):
        """
        Women in the SURVEILLANCE state will be screened even if they are outside the appropriate age range.
        """

        model = default_model(model_screening, age=age, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=negative_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == age
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    def test_surveillance_dna_negative(self, model_screening, negative_dna_result):
        """
        Women in the SURVEILLANCE state will move to the ROUTINE state after a negative DNA test result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=negative_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.ROUTINE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 1
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost

    def test_surveillance_dna_positive_16_18_cancer_negative(self, model_screening, positive_16_18_dna_result):
        """
        Women in the SURVEILLANCE state will be treated and stay in the SURVEILLANCE state after a positive DNA test
        result for strain 16 or 18 followed by a negative cancer inspection result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_16_18_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.NEGATIVE,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 3
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SURVEILLANCE_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost

    def test_surveillance_dna_positive_16_18_cancer_positive(self, model_screening, positive_16_18_dna_result):
        """
        Women in the SURVEILLANCE state will have their cancer detected and stay in the SURVEILLANCE state after a
        positive DNA test result for strain 16 or 18 followed by a positive cancer inspection result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(),
            dna_screening_test=MockScreeningTest(result=positive_16_18_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(result=ScreeningTestResult.CANCER,),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.DETECTED
        events = model.events.make_events()
        assert events.shape[0] == 2
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SURVEILLANCE_CANCER_INSPECTION.value
        assert events.Cost.values[1] == model.params.screening.cancer_inspection.cost

    def test_surveillance_dna_positive_other_high_via_negative(self, model_screening, positive_other_high_dna_result):
        """
        Women in the SURVEILLANCE state will move to the RE_TEST state after a positive DNA test result for a high
        risk strain other than 16 or 18 followed by a negative VIA test result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.NEGATIVE,),
            dna_screening_test=MockScreeningTest(result=positive_other_high_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)
        assert model.screening_state.values[unique_id] == ScreeningState.RE_TEST
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        print(events)
        assert events.shape[0] == 2
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SURVEILLANCE_VIA.value
        assert events.Cost.values[1] == model.params.screening.via.cost

    def test_surveillance_dna_positive_other_high_via_positive(self, model_screening, positive_other_high_dna_result):
        """
        Women in the SURVEILLANCE state will be treated and stay in the SURVEILLANCE state after a positive DNA test
        result for a high risk strain other than 16 or 18 followed by a positive VIA test result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.POSITIVE,),
            dna_screening_test=MockScreeningTest(result=positive_other_high_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.UNDETECTED
        events = model.events.make_events()
        assert events.shape[0] == 3
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SURVEILLANCE_VIA.value
        assert events.Cost.values[1] == model.params.screening.via.cost

    def test_surveillance_dna_positive_other_high_via_cancer(self, model_screening, positive_other_high_dna_result):
        """
        Women in the SURVEILLANCE state will have their cancer detected and stay in the SURVEILLANCE state after a
        positive DNA test result for a high risk strain other than 16 or 18 followed by a cancer VIA test result.
        """

        model = default_model(model_screening, age=40, last_screen_age=20, screening_state=ScreeningState.SURVEILLANCE)

        protocol = DnaThenViaScreeningProtocol(
            model=model,
            params=model.params.screening,
            via_screening_test=MockScreeningTest(result=ScreeningTestResult.CANCER,),
            dna_screening_test=MockScreeningTest(result=positive_other_high_dna_result,),
            cancer_inspection_screening_test=MockScreeningTest(),
        )
        protocol.apply(unique_id)

        assert model.screening_state.values[unique_id] == ScreeningState.SURVEILLANCE
        assert model.dicts.last_screen_age.get(unique_id, 0) == 40
        assert model.cancer_detection.values[unique_id] == CancerDetectionState.DETECTED
        events = model.events.make_events()
        assert events.shape[0] == 2
        assert events.Event.values[0] == Event.SURVEILLANCE_DNA.value
        assert events.Cost.values[0] == model.params.screening.dna.cost
        assert events.Event.values[1] == Event.SURVEILLANCE_VIA.value
        assert events.Cost.values[1] == model.params.screening.via.cost


__all__ = ["model_screening"]
