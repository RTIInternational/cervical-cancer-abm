from model.tests.fixtures import model_base
from model.state import HivState


def test_hiv(model_base):

    # ----- No one starts with HIV
    assert max(model_base.hiv.values) == HivState.NORMAL
    assert min(model_base.hiv.values) == HivState.NORMAL

    # ----- Update probabilities for 9 year olds
    model_base.hiv.transition_dict[(9,)] = 0.25
    model_base.hiv.update_probabilities()
    assert model_base.hiv.probabilities.mean() == 0.25

    # ----- Step
    model_base.hiv.step()
    assert model_base.hiv.values.mean() > 1.2
    assert model_base.hiv.values.mean() < 1.3


__all__ = ["model_base"]
