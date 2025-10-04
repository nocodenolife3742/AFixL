import logging
import pathlib
import tomllib
import time

from afixl.orchestration.models import Config
from afixl.backend.task import Task
from afixl.backend.fuzz.task import FuzzTask
from afixl.backend.repair.task import RepairTask
from afixl.backend.replay.task import ReplayTask
from afixl.backend.evaluate.task import EvaluateTask
from afixl.orchestration.crash import CrashRepository

logger = logging.getLogger(__name__)


class Manager:
    """
    A class to manage orchestration tasks of fuzz targets, including
    building, running, validating, and sanitizing them.
    """

    def __init__(self, path: str, timeout: int):
        """
        Initialize the Manager with the path to the fuzz target directory.

        Args:
            path (str): The path to the fuzz target directory.
            timeout (int): The maximum allowed execution time for the system under test in minutes.

        Raises:
            FileNotFoundError: If the specified path does not exist.
            NotADirectoryError: If the specified path is not a directory.

        Example:
            >>> manager = Manager("/path/to/fuzz/target")
            >>> print(manager.config)
        """
        # Initialize the Manager with the given path and timeout
        logger.info(
            f"Initializing Manager from {path} with a timeout of {timeout} minutes."
        )
        self._timeout = timeout
        self._start_time = time.time()

        # Initialize the crash repository
        self._crash_repository = CrashRepository()

        # Check if the config file exists and load it
        config_path = pathlib.Path(path) / "config.toml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")
        if not config_path.is_file():
            raise NotADirectoryError(f"Config path is not a file: {config_path}")

        # Load the configuration from the TOML file
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        data["path"] = str(pathlib.Path(path).resolve())
        self._config = Config.model_validate(data)
        logger.info(f"Configuration loaded from {config_path}")

        # Initialize the task list
        self._tasks: list[Task] = [
            FuzzTask(self._crash_repository, self._config, "fuzz"),
            ReplayTask(self._crash_repository, self._config, "replay"),
            RepairTask(self._crash_repository, self._config, "repair"),
            EvaluateTask(self._crash_repository, self._config, "evaluate"),
        ]

    def run(self):
        """
        Run all tasks managed by the Manager in sequence.

        This method iterates through each task in the task list and executes its run method.

        Example:
            >>> manager.run()
        """
        timeout_seconds = self._timeout * 60
        while (left_time := timeout_seconds - (time.time() - self._start_time)) > 0:
            for task in self._tasks:
                task.run()
            time.sleep(min(10, left_time))

    def __enter__(self):
        """
        Enter the context of the Manager.

        Returns:
            Manager: The instance itself for context management.
        """
        # Enter the context and return self
        for task in self._tasks:
            task.initialize()
            logger.info(f"Task {task._name} initialized.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context of the Manager.

        Args:
            exc_type: The type of exception raised, if any.
            exc_val: The value of the exception raised, if any.
            exc_tb: The traceback object, if any.
        """
        # Exit the context and close the manager
        self.close()

    def close(self):
        """
        Close the Manager and perform any necessary cleanup.

        This method is a placeholder for future cleanup logic.
        """
        # Close the manager and perform any necessary cleanup
        for task in self._tasks:
            task.close()
            logger.info(f"Task {task._name} closed.")
        logger.info("Manager closed.")
