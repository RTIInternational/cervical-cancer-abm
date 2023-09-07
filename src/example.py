from pathlib import Path
from model.cervical_model import CervicalModel
from model.logger import LoggerFactory
from time import time


if __name__ == "__main__":
    ts = time()
    scenario_dir = Path("experiments/zambia/scenario_base")
    model = CervicalModel(scenario_dir, 0, logger=LoggerFactory().create_logger("log"))
    model.run()
    print(f"Total time: {time() - ts}")
