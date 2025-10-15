from typing import override
import logging
import pathlib
import tarfile
import io

from afixl.backend.task import Task
from afixl.docker.instance import Instance
from afixl.orchestration.models import Crash
from afixl.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


class EvaluateTask(Task):
    """
    EvaluateTask is a specific implementation of Task that handles evaluation operations.
    """

    @override
    def initialize(self):
        """
        Initialize the evaluation task.
        This method should be called before running the task.
        """
        self._docker_instance: Instance = None
        self._evaluate_handle = None
        self._evaluating_crash: Crash = None
        self._build_handle = None

    @override
    def close(self):
        """
        Close the evaluation task and perform any necessary cleanup.
        This method should be called when the task is no longer needed.
        """
        if self._docker_instance:
            self._docker_instance.close()

    @override
    def run(self):
        """
        Run the evaluation task.
        This method should contain the logic for executing the evaluation process.
        """
        crashes = self._crash_repository.get_crashes(lambda c: c.stage == "repair")
        if len(crashes) > 0 and self._docker_instance is None:
            self._evaluating_crash = crashes[0]
            logger.info(f"Evaluating crash {self._evaluating_crash.id}")

            self._docker_instance = Instance(
                source=pathlib.Path(self._config.path),
                mode="build",
            )

            success = self._patch_application()
            if not success:
                logger.error(
                    f"Failed to apply patches for crash {self._evaluating_crash.id}"
                )
                self._evaluating_crash.stage = "replay"
                self._crash_repository.update_crash(self._evaluating_crash)
                self._docker_instance.close()
                self._docker_instance = None
                self._evaluating_crash = None
                return

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
            self._build_handle = self._docker_instance.execute(
                command="./build.sh",
                workdir="/src",
                environment=env_var,
            )

        if self._build_handle and not self._build_handle.running:
            exit_code = self._build_handle.exit_code
            self._build_handle = None
            if exit_code != 0:
                logger.info(
                    f"Failed to build the application for crash {self._evaluating_crash.id}"
                )
                self._evaluating_crash.stage = "replay"
                self._crash_repository.update_crash(self._evaluating_crash)
                self._docker_instance.close()
                self._docker_instance = None
                self._evaluating_crash = None
                return
            
            tar_bytes = io.BytesIO()
            with tarfile.open(fileobj=tar_bytes, mode="w") as tar:
                info = tarfile.TarInfo(name=self._evaluating_crash.id)
                info.size = len(self._evaluating_crash.input)
                tar.addfile(
                    tarinfo=info, fileobj=io.BytesIO(self._evaluating_crash.input)
                )
            tar_bytes.seek(0)
            self._docker_instance.write("/eval", tar_bytes)

            self._evaluate_handle = self._docker_instance.execute(
                command=f"timeout 10s ./{self._config.project.executable} /eval/{self._evaluating_crash.id}",
                workdir="/exe",
                environment=self._config.environment.runtime,
            )

        if self._evaluate_handle and not self._evaluate_handle.running:
            if self._evaluate_handle.exit_code == 0:
                logger.info(f"Crash {self._evaluating_crash.id} is fixed.")
                self._evaluating_crash.valid_patches = self._evaluating_crash.history[
                    -1
                ].patches
                self._evaluating_crash.stage = "evaluate"

                # Save the valid patches to a file
                patches_file = (
                    PROJECT_ROOT / "patches" / f"{self._evaluating_crash.id}.json"
                )
                patches_file.parent.mkdir(parents=True, exist_ok=True)
                with open(patches_file, "w") as f:
                    json_bytes = self._evaluating_crash.model_dump_json(
                        indent=2
                    ).encode("utf-8")
                    f.write(json_bytes.decode("utf-8"))
            else:
                logger.info(f"Crash {self._evaluating_crash.id} is not fixed.")
                self._evaluating_crash.stage = "replay"
            self._crash_repository.update_crash(self._evaluating_crash)
            self._evaluate_handle = None
            self._docker_instance.close()
            self._docker_instance = None
            self._evaluating_crash = None

    def _patch_application(self):
        """
        Apply the proposed patches to the source code.
        This method should contain the logic for applying patches.
        """
        if not self._docker_instance:
            raise ValueError("Instance is not set.")

        patches = self._evaluating_crash.history[-1].patches
        for patch in patches:
            processed_lines = set()
            file_path = patch.file
            raw_content = self._get_file_content(str(file_path), raw=True)
            lines = raw_content.splitlines(keepends=True)

            for modified_line in patch.diff:
                line_number = modified_line.line_number - 1
                if 0 <= line_number < len(lines) and line_number not in processed_lines:
                    lines[line_number] = "\n".join(modified_line.content) + "\n"
                    processed_lines.add(line_number)
                else:
                    if line_number in processed_lines:
                        logger.error(
                            f"Line {line_number + 1} in file {file_path} has already been modified."
                        )
                    else:
                        logger.error(
                            f"Line {line_number + 1} in file {file_path} is out of range."
                        )
                    return False

            new_content = "".join(lines)
            tar_bytes = io.BytesIO()
            with tarfile.open(fileobj=tar_bytes, mode="w") as tar:
                info = tarfile.TarInfo(name=pathlib.Path(file_path).name)
                info.size = len(new_content.encode("utf-8"))
                tar.addfile(
                    tarinfo=info, fileobj=io.BytesIO(new_content.encode("utf-8"))
                )
            tar_bytes.seek(0)
            self._docker_instance.write(str(pathlib.Path(file_path).parent), tar_bytes)

        return True

    def _get_file_content(self, file_path: str, raw: bool = False) -> str:
        """
        Read and return the content of a file.
        Args:
            file_path (str): The path to the file.
        Returns:
            str: The content of the file.
        """

        if not self._docker_instance:
            raise ValueError("Instance is not set.")

        tar_bytes = self._docker_instance.read(file_path)
        with tarfile.open(fileobj=tar_bytes, mode="r:*") as tar:
            member_count = len(tar.getmembers())
            if member_count != 1:
                raise ValueError(
                    f"Expected one member in tar archive, found {member_count}: {file_path}"
                )

            for member in tar:
                if not member.isfile():
                    raise ValueError(
                        f"Expected a file in tar archive, found {member.type}"
                    )
                file = tar.extractfile(member)
                if file:
                    raw_content = file.read().decode("utf-8")
                    if raw:
                        return raw_content
                    content = "\n".join(
                        f"{i + 1:4d} {line}"
                        for i, line in enumerate(raw_content.splitlines())
                    )
                    return content
                else:
                    raise ValueError(
                        f"Could not extract file from tar archive: {file_path}"
                    )
