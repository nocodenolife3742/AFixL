from typing import override
import logging
import pathlib
import tarfile

from afixl.backend.task import Task
from afixl.docker.instance import Instance
from afixl.docker.exec_handle import ExecHandle
from afixl.orchestration.models import Crash

logger = logging.getLogger(__name__)


class FuzzTask(Task):
    """
    FuzzTask is a specific implementation of Task that handles fuzzing operations.
    """

    @override
    def initialize(self):
        """
        Initialize the fuzzing task.
        This method should be called before running the task.
        """
        # Initialize the Docker instance for fuzzing
        self._docker_instance = Instance(
            source=pathlib.Path(self._config.path),
            mode="build",
            no_cache=True,
        )
        self._fuzz_handle: ExecHandle = None
        self._is_resuming = False
        self._seen_crashes = set()

        # Build the target for fuzzing
        self._build_target()

    @override
    def close(self):
        """
        Close the fuzzing task and perform any necessary cleanup.
        This method should be called when the task is no longer needed.
        """
        if self._docker_instance:
            self._docker_instance.close()

    @override
    def run(self):
        """
        Run the fuzzing task.
        This method should contain the logic for executing the fuzzing process.
        """
        # Start the fuzzing process if not already running
        if not self._fuzz_handle:
            fuzz_command = f"afl-fuzz -i {'-' if self._is_resuming else '/eval'} -o /out -V 60 -- ./{self._config.project.executable} @@"
            self._fuzz_handle = self._docker_instance.execute(
                command=fuzz_command,
                workdir="/exe",
                environment=self._config.environment.runtime,
            )
            self._is_resuming = True

        # If the command is not running, add crashes to the repository and reset the handle
        if not self._fuzz_handle.running:

            # Extract crashes from the Docker container and add them to the crash repository
            with tarfile.open(
                fileobj=self._docker_instance.read("/out/default/crashes"), mode="r|*"
            ) as tar:
                for member in tar:

                    # Skip directories and non-files
                    if not member.isfile():
                        continue

                    # Extract the file and add it to the crash repository
                    file_obj = tar.extractfile(member)
                    file_name = pathlib.Path(member.name).name
                    if (
                        file_obj
                        and file_name.startswith("id:")
                        and file_name not in self._seen_crashes
                    ):
                        data = file_obj.read()
                        self._crash_repository.add_crash(
                            Crash(
                                stage="fuzz",
                                input=data,
                            )
                        )
                        self._seen_crashes.add(file_name)

            # Reset the fuzz handle to allow restarting the fuzzing process
            self._fuzz_handle = None

    def _build_target(self):
        """
        Build the target for fuzzing.
        This method should contain the logic for building the target application.
        """
        # Set up environment variables for AFL++
        base_env_vars = {
            "CXX": "afl-clang-fast++",
            "CC": "afl-clang-fast",
            "CXXFLAGS": f"-Wall -Wextra -std={self._config.project.standard}",
            "CFLAGS": f"-Wall -Wextra -std={self._config.project.standard}",
            "LD": f"{self._config.project.standard.startswith('c++') and 'afl-clang-fast++' or 'afl-clang-fast'}",
            "AFL_USE_ASAN": "1",
            "AFL_USE_UBSAN": "1",
        }
        env_var = self._config.environment.build.copy()
        env_var.update(base_env_vars)

        # Execute the build command inside the Docker container
        result = self._docker_instance.execute(
            command="./build.sh",
            workdir="/src",
            environment=env_var,
        )
        while result.running:
            pass

        # Check the result of the build command
        if result.exit_code != 0:
            logger.error(f"Task {self._name} build failed.")
            raise RuntimeError("Build failed.")
        logger.info(f"Task {self._name} build completed successfully.")
