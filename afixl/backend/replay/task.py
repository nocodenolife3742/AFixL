from typing import override
import logging
import pathlib
import tarfile
import io

from afixl.backend.task import Task
from afixl.docker.instance import Instance
from afixl.docker.exec_handle import ExecHandle


logger = logging.getLogger(__name__)


class ReplayTask(Task):
    """
    ReplayTask is a specific implementation of Task that handles replay operations.
    """

    @override
    def initialize(self):
        """
        Initialize the replay task.
        This method should be called before running the task.
        """
        self._docker_instance = Instance(
            source=pathlib.Path(self._config.path),
            mode="build",
        )
        self._replay_handle: ExecHandle = None
        self._replaying_crash = None

        # Build the target for replaying
        self._build_target()

    @override
    def close(self):
        """
        Close the replay task and perform any necessary cleanup.
        This method should be called when the task is no longer needed.
        """
        if self._docker_instance:
            self._docker_instance.close()

    @override
    def run(self):
        """
        Run the replay task.
        This method should contain the logic for executing the replay process.
        """
        # Replay each crash in the crash repository
        if not self._replay_handle:

            crashes = self._crash_repository.get_crashes(
                lambda c: c.stage == "fuzz" and c.reproducable is None
            )
            if crashes:
                self._replaying_crash = crashes[0]
                logger.info(f"Replaying crash {self._replaying_crash.id}")

                tar_bytes = io.BytesIO()
                with tarfile.open(fileobj=tar_bytes, mode="w") as tar:
                    info = tarfile.TarInfo(name=self._replaying_crash.id)
                    info.size = len(self._replaying_crash.input)
                    tar.addfile(
                        tarinfo=info, fileobj=io.BytesIO(self._replaying_crash.input)
                    )
                tar_bytes.seek(0)
                self._docker_instance.write("/eval", tar_bytes)

                self._replay_handle = self._docker_instance.execute(
                    command=f"./{self._config.project.executable} /eval/{self._replaying_crash.id}",
                    workdir="/exe",
                    environment=self._config.environment.runtime,
                )

        if self._replay_handle and not self._replay_handle.running:
            output = self._replay_handle.output.decode()
            exit_code = self._replay_handle.exit_code
            if exit_code != 0 and (
                "ERROR: AddressSanitizer" in output
                or "ERROR: UndefinedBehaviorSanitizer" in output
            ):
                logger.info(f"Crash {self._replaying_crash.id} is reproducible.")
                self._replaying_crash.reproducable = True
                self._replaying_crash.report = output.encode("utf-8")
            else:
                logger.info(f"Crash {self._replaying_crash.id} is not reproducible.")
                self._replaying_crash.reproducable = False
            self._replaying_crash.stage = "replay"
            self._crash_repository.update_crash(self._replaying_crash)
            self._replay_handle = None
            self._replaying_crash = None

    def _build_target(self):
        """
        Build the target for fuzzing.
        This method should contain the logic for building the target application.
        """
        # Set up environment variables for the build process
        base_env_vars = {
            "CXX": "g++",
            "CC": "gcc",
            "CXXFLAGS": f"-Wall -Wextra -std={self._config.project.standard} -fsanitize=address,undefined -g",
            "CFLAGS": f"-Wall -Wextra -std={self._config.project.standard} -fsanitize=address,undefined -g",
            "LD": f"{self._config.project.standard.startswith('c++') and 'g++' or 'gcc'}",
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
