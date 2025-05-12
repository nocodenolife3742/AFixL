from AfixL.engine import Engine
from AfixL.logging_config import setup_logging
from AfixL.fuzz.core import build, fuzz, replay
from AfixL.fuzz.crash import Crash, CrashType
from pathlib import Path
import logging
import tomllib
import time
import math

# TODO: change to 60 * 10 when project is ready
MAX_FUZZ_PHASE_TIME = 60 * 1  # 10 minutes


class Controller:
    """
    A class to control the main flow of the fuzzing and fix process.
    """

    def __init__(self, project_dir: Path, timeout: int = 360):
        """
        Initialize the Controller with the project directory.

        Args:
            project_dir (Path): The path to the project directory.
            timeout (int): The timeout for the fuzzing process in minutes.
        """

        # Check if the timeout is valid
        if timeout <= 0:
            raise ValueError("Timeout must be greater than 0 minutes.")
        # TODO: Uncomment this check if needed
        # if timeout < 20:
        #    raise ValueError("Not enough time for fuzzing and fixing. Set timeout to at least 20 minutes.")

        # Initialize the crash bucket
        self.crash_bucket: list[Crash] = []

        # Record the start time
        self.start_time = time.time()

        # Set up logging
        setup_logging()
        self.logger = logging.getLogger(__name__)

        # Set the project directory and timeout
        if not project_dir.exists():
            self.logger.error(f"Project directory {project_dir} not found.")
            raise FileNotFoundError(f"Project directory {project_dir} not found.")
        self.project_dir = project_dir
        self.timeout = timeout

        # Initialize the engine of the fuzzing tool
        self.logger.info(f"Initializing engine with project directory: {project_dir}")
        self.fuzz_engine = Engine(str(project_dir))

        # Load the configuration file
        config_file = project_dir / "config.toml"
        if not config_file.exists():
            self.logger.error(f"Configuration file {config_file} not found.")
            raise FileNotFoundError(f"Configuration file {config_file} not found.")
        with open(config_file, "rb") as f:
            self.config = tomllib.load(f)

        # Build the fuzz targets using the specified build command
        self.logger.info("Building targets...")
        status = build(self.fuzz_engine, "fuzz", self.config)
        if not status:
            self.logger.error("Build failed. Exiting.")
            return {}

    def _check_timeout(self) -> bool:
        """
        Check if the timeout has been reached.

        Returns:
            bool: True if the timeout has been reached, False otherwise.
        """
        return time.time() - self.start_time >= self.timeout * 60

    def run_fuzzing(self) -> dict[str, str]:
        """
        Run the fuzzing process to find crashes.

        Returns:
            dict[str, str]: A dictionary containing the found crashes. File names
                            are the keys, and their paths are the values.
        """
        self.logger.info("Starting fuzzing...")

        # Calculate the time left for the fuzzing phase
        left_time = math.floor(self.timeout * 60 - (time.time() - self.start_time))
        if left_time > MAX_FUZZ_PHASE_TIME:
            left_time = MAX_FUZZ_PHASE_TIME
        if left_time <= 0:
            self.logger.info("Timeout reached. Exiting.")
            return {}
        self.logger.info(f"Time left for this phase: {left_time / 60:.2f} minutes")

        # Run the fuzzing command
        status = fuzz(self.fuzz_engine, self.config, timeout=left_time)
        if not status:
            self.logger.error("Fuzzing failed. Exiting.")
            return {}

        # Load all the crashes files and return them
        self.logger.info("Fuzzing completed. Loading crash files...")
        files = self.fuzz_engine.get_files("/out/default/crashes")
        files = {k: v for k, v in files.items() if k.startswith("id:")}
        if not files:
            self.logger.info("No crash files found.")
        return files

    def run_replay(self):
        """
        Run the replay process to check if the crashes are reproducible.
        """

        self.logger.info("Running replay process...")

        # Iterate through the crash bucket and replay each crash
        # that has not been tested yet
        for index, crash in enumerate(self.crash_bucket):

            # Check if the crash has already been tested
            if crash.type != CrashType.NOT_TESTED:
                self.logger.info(f"Crash {crash.input_file} already tested.")
                continue

            # Build the replay target
            self.logger.info(f"Building replay target for crash {crash.input_file}...")
            engine = Engine(str(self.project_dir))
            status = build(engine, "replay", self.config)
            if not status:
                self.logger.error("Replay build failed. Exiting.")
                return

            # Replay the crash and check if it is reproducible
            self.logger.info(f"Replaying crash {crash.input_file}...")
            modified_crash = replay(
                engine,
                crash,
                self.config,
            )
            self.crash_bucket[index] = modified_crash

    def run_fix(self):
        """
        Run the fix process to fix the crashes.
        """
        self.logger.info("Running fix process...")
        # TODO: Implement the fix phase
        pass

    def run_main(self):
        """
        Run the main process of the controller.
        """
        self.logger.info("Running main process...")

        # While the timeout is not reached, continue the main process
        while not self._check_timeout():
            self.logger.info("Running fuzzing process...")

            # Run fuzz phase
            crash_files = self.run_fuzzing()
            crashes = [
                Crash(
                    input_file=k,
                    input_content=v,
                )
                for k, v in crash_files.items()
            ]

            # Add the new crashes to the crash bucket
            self.logger.info("Adding new crashes to the crash bucket...")
            for crash in crashes:
                if crash not in self.crash_bucket:
                    self.crash_bucket.append(crash)
                    self.logger.info(f"New crash found: {crash.input_file}")

            # Check if the timeout is reached after fuzzing
            if self._check_timeout():
                self.logger.info("Timeout reached. Exiting.")
                break

            # Get the report from the ASAN and UBSAN
            self.logger.info("Checking for ASAN and UBSAN reports...")
            self.run_replay()

            # Check if the timeout is reached after replay
            if self._check_timeout():
                self.logger.info("Timeout reached. Exiting.")
                break

            # Run the fix phase
            # TODO: Implement the fix phase
            self.run_fix()
