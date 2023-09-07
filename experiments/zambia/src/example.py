from pathlib import Path

from model.cervical_model import CervicalModel
from model.logger import LoggerFactory


if __name__ == "__main__":
    scenario_dir = Path("experiments/zambia/scenario_base")
    model = CervicalModel(scenario_dir=scenario_dir, iteration=0, logger=LoggerFactory().create_logger("log"))
    model.run()
