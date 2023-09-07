from pathlib import Path
import pytest

from model.logger import LoggerFactory
from model.cervical_model import CervicalModel


@pytest.fixture(scope="session")
def model_base():
    scenario_dir = Path("experiments/zambia/scenario_base/")
    model_base = CervicalModel(scenario_dir, 0, logger=LoggerFactory().create_logger())
    return model_base


@pytest.fixture(scope="function")
def model_screening():
    scenario_dir = Path("experiments/zambia/scenario_screening/")
    model_screening = CervicalModel(scenario_dir, 0, logger=LoggerFactory().create_logger())
    return model_screening


@pytest.fixture(scope="session")
def model_vaccination():
    scenario_dir = Path("experiments/zambia/scenario_vaccination/")
    model = CervicalModel(scenario_dir, 0, logger=LoggerFactory().create_logger())
    model_vaccination = model
    return model_vaccination
