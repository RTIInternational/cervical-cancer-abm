import collections
import itertools

import pytest
import scipy.stats
import pandas as pd
from model.screening import CancerInspectionScreeningTest, DnaScreeningTest, ScreeningTestResult, ViaScreeningTest
from model.state import CancerState, HpvState, HpvStrain
from model.tests.fixtures import model_screening


Case = collections.namedtuple("Case", ["truth", "sensitive", "specific", "expected", "exception"])
n_tries = 1000
prob_pass = 0.999


class TestCancerInspectionScreeningTest:
    @staticmethod
    def create_cases():
        """
        Return a list of `Case` objects comprising all combinations of CancerState,
        sensitivity (0 and 1 only), and specificity (0 and 1 only).
        """

        cases = []

        states = list(s for s in CancerState)
        detectable = [CancerState.REGIONAL, CancerState.DISTANT]

        for params in itertools.product(states, (True, False), (True, False)):
            truth = params[0]
            is_sensitive = params[1]
            is_specific = params[2]

            exception = None

            if truth == CancerState.DEAD:
                expected = None
                exception = ValueError
            elif truth in detectable:
                if is_sensitive:
                    expected = ScreeningTestResult.CANCER
                else:
                    expected = ScreeningTestResult.NEGATIVE
            else:
                if is_specific:
                    expected = ScreeningTestResult.NEGATIVE
                else:
                    expected = ScreeningTestResult.CANCER

            cases.append(
                Case(truth=truth, sensitive=is_sensitive, specific=is_specific, expected=expected, exception=exception)
            )

        return cases

    def test_cancer_inspection_result(self, model_screening):
        """
        The screening test should return the expected result under all combinations of valid inputs.
        """

        for case in TestCancerInspectionScreeningTest.create_cases():
            sensitivity = 1 if case.sensitive else 0
            specificity = 1 if case.specific else 0

            model_screening.params.screening.cancer_inspection.sensitivity = sensitivity
            model_screening.params.screening.cancer_inspection.specificity = specificity

            t = CancerInspectionScreeningTest(model_screening)

            if case.exception is None:
                assert t.get_result(case.truth) == case.expected
            else:
                with pytest.raises(case.exception):
                    t.get_result(case.truth)

    @pytest.mark.parametrize("sensitivity", (0.3, 0.8))
    def test_sensitivity(self, model_screening, sensitivity):
        """
        When a woman has cancer, the number of positive screening test results should match the expectation
        based on the sensitivity rate.

        With sensitivities other than 0 or 1, the screening test result is a random process. This unit test runs the
        screening test many times, counts the number of positive results, and verifies that the number is within the
        interval we'd expect based on the statistical properties of the random process. Due to the statistical nature
        of this unit test, it will eventually fail if it's run many times. The chance of it failing two consecutive
        times is exceedingly low, however, and would almost certainly point to a real problem in the code.
        """

        model_screening.params.screening.cancer_inspection.sensitivity = sensitivity

        t = CancerInspectionScreeningTest(model_screening)
        v = ScreeningTestResult.CANCER

        observed = pd.Series([t.get_result(CancerState.REGIONAL).value for _ in range(n_tries)]).value_counts().loc[v]

        expected = scipy.stats.binom(n_tries, sensitivity).interval(prob_pass)

        assert expected[0] <= observed and observed <= expected[1]

    @pytest.mark.parametrize("specificity", (0.3, 0.8))
    def test_specificity(self, model_screening, specificity):
        """
        When a woman doesn't have cancer, the number of negative screening test results should match the expectation
        based on the specificity rate.

        See TestCancerInspectionScreeningTest.test_sensitivity for details about the random nature of this test.
        """

        model_screening.params.screening.cancer_inspection.specificity = specificity

        t = CancerInspectionScreeningTest(model_screening)
        v = ScreeningTestResult.NEGATIVE

        observed = pd.Series([t.get_result(CancerState.NORMAL).value for _ in range(n_tries)]).value_counts().loc[v]

        expected = scipy.stats.binom(n_tries, specificity).interval(prob_pass)

        assert expected[0] <= observed and observed <= expected[1]


class TestCancerInspectionScreeningTestHelpers:
    """
    Test the helper functions defined in the TestCancerInspectionScreeningTest class.
    """

    def test_number_of_cases(self):
        """
        The cases should be all possible combinations of inputs. Test that the number of cases matches the number of
        combinations.
        """

        observed = len(TestCancerInspectionScreeningTest.create_cases())
        expected = len(CancerState) * 2 * 2
        assert observed == expected


class TestDnaScreeningTest:
    @staticmethod
    def create_cases():
        """
        Return a list of `Case` objects comprising all combinations of HpvState for each strain, sensitivity
        (0 and 1 only), and specificity (0 and 1 only).
        """

        cases = []

        detectable = [HpvStrain.SIXTEEN, HpvStrain.EIGHTEEN, HpvStrain.HIGH_RISK]

        for params in itertools.product((True, False), repeat=6):
            has = {}
            has[HpvStrain.SIXTEEN] = params[0]
            has[HpvStrain.EIGHTEEN] = params[1]
            has[HpvStrain.HIGH_RISK] = params[2]
            has[HpvStrain.LOW_RISK] = params[3]
            is_sensitive = params[4]
            is_specific = params[5]

            expected = {strain: ScreeningTestResult.NEGATIVE for strain in HpvStrain}

            if any([has[strain] for strain in detectable]):
                if is_sensitive:
                    for strain in detectable:
                        if has[strain]:
                            expected[strain] = ScreeningTestResult.POSITIVE
                else:
                    pass
            else:
                if is_specific:
                    pass
                else:
                    expected[HpvStrain.HIGH_RISK] = ScreeningTestResult.POSITIVE

            for truth in TestDnaScreeningTest.get_equivalent_truths(has):
                cases.append(
                    Case(truth=truth, sensitive=is_sensitive, specific=is_specific, expected=expected, exception=None,)
                )

        return cases

    @staticmethod
    def get_equivalent_truths(has_strains):
        """
        Given a boolean status for each HpvStrain, return the list of all HpvState combinations that are equivalent
        to that status in the context of the "truth" passed to the DNA screening test.

        Arguments
        ---------
        has_strains: Dictionary mapping each HpvStrain to a boolean indicating whether the woman has that strain of HPV.

        Returns
        -------
        List of dictionaries mapping each HpvStrain to an HpvState.
        """

        strains = list(has_strains.keys())
        equivalent_states = []

        for strain in strains:
            if has_strains[strain]:
                equivalent_states.append(list(state for state in HpvState if state != HpvState.NORMAL))
            else:
                equivalent_states.append([HpvState.NORMAL])

        for states in itertools.product(*equivalent_states):
            truth = {}
            for i, state in enumerate(states):
                truth[strains[i]] = states[i]
            yield truth

    @staticmethod
    def sort_truths(truths):
        """
        Sort a list of truth dictionaries by the HpvState assigned to each HpvStrain.
        """
        return sorted(truths, key=lambda x: tuple(x[s] for s in HpvStrain))

    def test_dna_test_result(self, model_screening):
        """
        The screening test should return the expected result under all combinations
        of valid inputs.
        """

        for case in TestDnaScreeningTest.create_cases():

            model_screening.params.screening.dna.sensitivity = 1 if case.sensitive else 0
            model_screening.params.screening.dna.specificity = 1 if case.specific else 0

            t = DnaScreeningTest(model_screening)

            if case.exception is None:
                assert t.get_result(case.truth) == case.expected
            else:
                with pytest.raises(case.exception):
                    t.get_result(case.truth)

    @pytest.mark.parametrize("sensitivity", (0.3, 0.8))
    def test_sensitivity(self, model_screening, sensitivity):
        """
        When a woman has a detectable HPV strain, the number of positive screening test results for that strain
        should match the expectation based on the sensitivity rate.

        See TestCancerInspectionScreeningTest.test_sensitivity for details about the random nature of this test.
        """

        model_screening.params.screening.dna.sensitivity = sensitivity

        t = DnaScreeningTest(model_screening)

        truth = {s: HpvState.NORMAL for s in HpvStrain}
        truth[HpvStrain.SIXTEEN] = HpvState.CIN_1

        results = [t.get_result(truth) for _ in range(n_tries)]
        observed = len([r for r in results if r[HpvStrain.SIXTEEN] == ScreeningTestResult.POSITIVE])
        expected = scipy.stats.binom(n_tries, sensitivity).interval(prob_pass)

        assert expected[0] <= observed and observed <= expected[1]

    @pytest.mark.parametrize("specificity", (0.3, 0.8))
    def test_specificity(self, model_screening, specificity):
        """
        When a woman doesn't have a detectable HPV strain, the number of negative screening test results should match
        the expectation based on the specificity rate.

        See TestCancerInspectionScreeningTest.test_sensitivity for details about the random nature of this test.
        """

        model_screening.params.screening.dna.specificity = specificity

        t = DnaScreeningTest(model_screening)

        truth = {s: HpvState.NORMAL for s in HpvStrain}
        results = [t.get_result(truth) for _ in range(n_tries)]
        observed = len([r for r in results if all(r[s] == ScreeningTestResult.NEGATIVE for s in HpvStrain)])

        expected = scipy.stats.binom(n_tries, specificity).interval(prob_pass)

        assert expected[0] <= observed and observed <= expected[1]


class TestDnaScreeningTestHelpers:
    """
    Test the helper functions defined in the TestDnaScreeningTest class.
    """

    def test_number_of_cases(self):
        """
        The cases should be all possible combinations of inputs. Test that the number of cases matches the number of
        combinations.
        """

        observed = len(TestDnaScreeningTest.create_cases())
        expected = len(HpvState) ** 4 * 2 * 2
        assert observed == expected

    def test_equivalent_truths_none(self):
        """
        When a woman has no strains, the only equivalency is the NORMAL state for all strains.
        """

        has = {s: False for s in HpvStrain}
        observed = list(TestDnaScreeningTest.get_equivalent_truths(has))
        expected = [{s: HpvState.NORMAL for s in HpvStrain}]
        assert observed == expected

    def test_equivalent_truths_one(self):
        """
        When a woman has one strain, there should be one equivalency for each non-NORMAL state in that strain.
        All other strains should be fixed in the NORMAL state.
        """

        has = {s: False for s in HpvStrain}
        has[HpvStrain.SIXTEEN] = True

        observed = TestDnaScreeningTest.sort_truths(list(TestDnaScreeningTest.get_equivalent_truths(has)))

        expected = []
        for state in HpvState:
            if state == HpvState.NORMAL:
                continue
            truth = {s: HpvState.NORMAL for s in HpvStrain}
            truth[HpvStrain.SIXTEEN] = state
            expected.append(truth)
        expected = TestDnaScreeningTest.sort_truths(expected)

        assert observed == expected

    def test_equivalent_truths_multi(self):
        """
        When a woman has multiple strains, there should be one equivalency for each combination of non-NORMAL states
        in those strains. All other strains should be fixed in the NORMAL state.
        """

        has = {s: False for s in HpvStrain}
        has[HpvStrain.SIXTEEN] = True
        has[HpvStrain.LOW_RISK] = True

        observed = TestDnaScreeningTest.sort_truths(list(TestDnaScreeningTest.get_equivalent_truths(has)))

        expected = []
        for state_sixteen in HpvState:
            if state_sixteen == HpvState.NORMAL:
                continue
            for state_low in HpvState:
                if state_low == HpvState.NORMAL:
                    continue
                truth = {s: HpvState.NORMAL for s in HpvStrain}
                truth[HpvStrain.SIXTEEN] = state_sixteen
                truth[HpvStrain.LOW_RISK] = state_low
                expected.append(truth)
        expected = TestDnaScreeningTest.sort_truths(expected)

        assert observed == expected


class TestViaScreeningTest:
    @staticmethod
    def create_cases():
        """
        Return a list of `Case` objects comprising all combinations of HpvState, CancerState, sensitivity
        (0 and 1 only), and specificity (0 and 1 only).
        """

        cases = []

        for params in itertools.product(HpvState, CancerState, (True, False), (True, False),):
            hpv = params[0]
            cancer = params[1]
            is_sensitive = params[2]
            is_specific = params[3]

            exception = None

            if cancer == CancerState.DEAD:
                expected = None
                exception = ValueError
            elif hpv == HpvState.CANCER and cancer == CancerState.NORMAL:
                expected = None
                exception = ValueError
            elif hpv in [HpvState.NORMAL, HpvState.HPV, HpvState.CIN_1]:
                if is_specific:
                    expected = ScreeningTestResult.NEGATIVE
                else:
                    expected = ScreeningTestResult.POSITIVE
            elif hpv == HpvState.CIN_2_3:
                if is_sensitive:
                    expected = ScreeningTestResult.POSITIVE
                else:
                    expected = ScreeningTestResult.NEGATIVE
            elif hpv == HpvState.CANCER and cancer == CancerState.LOCAL:
                if is_sensitive:
                    expected = ScreeningTestResult.CANCER
                else:
                    expected = ScreeningTestResult.NEGATIVE
            elif hpv == HpvState.CANCER and cancer in [CancerState.REGIONAL, CancerState.DISTANT]:
                expected = ScreeningTestResult.CANCER
            else:
                raise NotImplementedError()

            cases.append(
                Case(
                    truth={"true_hpv_state": hpv, "true_cancer_state": cancer},
                    sensitive=is_sensitive,
                    specific=is_specific,
                    expected=expected,
                    exception=exception,
                )
            )

        return cases

    def test_via_result(self, model_screening):
        """
        The screening test should return the expected result under all combinations of valid inputs.
        """

        for case in TestViaScreeningTest.create_cases():
            sensitivity = 1 if case.sensitive else 0
            specificity = 1 if case.specific else 0

            model_screening.params.screening.via.sensitivity = sensitivity
            model_screening.params.screening.via.specificity = specificity

            t = ViaScreeningTest(model_screening)

            if case.exception is None:
                assert t.get_result(**case.truth) == case.expected
            else:
                with pytest.raises(case.exception):
                    t.get_result(**case.truth)

    @pytest.mark.parametrize("sensitivity", (0.3, 0.8))
    def test_sensitivity(self, model_screening, sensitivity):
        """
        When a woman's HPV state is detectable by the VIA test, the number of positive screening test results
        should match the expectation based on the sensitivity rate.

        See TestCancerInspectionScreeningTest.test_sensitivity for details about the random nature of this test.
        """

        model_screening.params.screening.via.sensitivity = sensitivity

        t = ViaScreeningTest(model_screening)
        observed = (
            pd.Series([t.get_result(HpvState.CIN_2_3, CancerState.NORMAL).value for _ in range(n_tries)])
            .value_counts()
            .loc[ScreeningTestResult.POSITIVE]
        )

        expected = scipy.stats.binom(n_tries, sensitivity).interval(prob_pass)

        assert expected[0] <= observed and observed <= expected[1]

    @pytest.mark.parametrize("specificity", (0.3, 0.8))
    def test_specificity(self, model_screening, specificity):
        """
        When a woman doesn't have HPV or cancer, the number of negative screening test results should match the
        expectation based on the specificity rate.

        See TestCancerInspectionScreeningTest.test_sensitivity for details about the random nature of this test.
        """

        model_screening.params.screening.via.specificity = specificity

        t = ViaScreeningTest(model_screening)
        observed = (
            pd.Series([t.get_result(HpvState.NORMAL, CancerState.NORMAL).value for _ in range(n_tries)])
            .value_counts()
            .loc[ScreeningTestResult.NEGATIVE]
        )

        expected = scipy.stats.binom(n_tries, specificity).interval(prob_pass)

        assert expected[0] <= observed and observed <= expected[1]


class TestViaScreeningTestHelpers:
    """
    Test the helper functions defined in the TestViaScreeningTest class.
    """

    def test_number_of_cases(self):
        """
        The cases should be all possible combinations of inputs. Test that the number of cases matches the number of
        combinations.
        """

        observed = len(TestViaScreeningTest.create_cases())
        expected = len(HpvState) * len(CancerState) * 2 * 2
        assert observed == expected


__all__ = ["model_screening"]
