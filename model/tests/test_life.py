from model.tests.fixtures import model_base
from model.state import LifeState, AgeGroup, CancerState, HivState


def test_initiation(model_base):
    # All should be alive
    assert all(model_base.life.values == LifeState.ALIVE)


def test_life_probabilities(model_base):
    # The transition dict should contain all possible keys
    assert len(model_base.life.transition_dict) == len(AgeGroup) * len(HivState) * len(CancerState)


def test_update_probabilities(model_base):
    # Probabilities should update based on age of women in model_base
    model_base.age = 100
    model_base.life.update_probabilities()
    assert round(model_base.life.probabilities.mean(), 5) == round(model_base.life.transition_dict[(100, 1, 1)], 5)


def test_life_step(model_base):
    # Women should die in the model
    model_base.life.probabilities.fill(0.5)
    model_base.life.step()
    assert model_base.life.values.mean() > 1.4
    assert model_base.life.values.mean() < 1.6


__all__ = ["model_base"]
