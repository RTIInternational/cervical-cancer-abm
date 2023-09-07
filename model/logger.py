import logging
import uuid


class LoggerFactory:
    def __init__(self, level=logging.DEBUG):
        self.level = level

    def create_logger(self, log_file: str = "log"):
        logger = logging.getLogger(str(uuid.uuid4()))
        logger.setLevel(self.level)

        handler = logging.FileHandler(filename=log_file, mode="w")
        formatter = logging.Formatter(fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger
