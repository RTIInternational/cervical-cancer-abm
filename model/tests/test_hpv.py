from model.tests.fixtures import model_base
from model.state import HpvState, CancerState


def test_hpv_initiation(model_base):

    # ----- No one starts with HPV
    assert max(model_base.max_hpv_state.values) == HpvState.NORMAL
    assert min(model_base.max_hpv_state.values) == HpvState.NORMAL
    for strain in model_base.hpv_strains.values():
        assert max(strain.values) == HpvState.NORMAL


def test_hpv_updates(model_base):

    # ----- If selected - test that appropriate events follow
    # --- Set probability to 1 so that everyone is selected
    model_base.hpv_strains[1].probabilities.fill(1)
    model_base.hpv_strains[1].step()
    # --- Everyone should have changed
    assert model_base.hpv_strains[1].values.min() == HpvState.HPV
    assert model_base.hpv_strains[1].values.max() == HpvState.HPV

    # ----- If transition to cancer, lots of things occurs
    model_base.hpv_strains[1].probabilities.fill(1)
    model_base.hpv_strains[1].values.fill(HpvState.CIN_2_3)

    # --- Find those who have cancer
    model_base.hpv_strains[1].step()
    unique_ids = model_base.unique_ids[model_base.hpv_strains[1].values == HpvState.CANCER]
    # All should have cancer
    assert min(model_base.cancer.values[unique_ids]) == CancerState.LOCAL
    # All should be able to transition further
    for unique_id in unique_ids:
        assert model_base.cancer.probabilities[unique_id] > 0


__all__ = ["model_base"]
