from typing import override
import logging
from pydantic_ai import Agent
import asyncio
import threading
import tarfile
import pathlib

from afixl.backend.task import Task
from afixl.docker.instance import Instance
from afixl.orchestration.models import (
    RequestCode,
    ProposedPatch,
    MakeNote,
    Crash,
)
from afixl.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


class RepairTask(Task):
    """
    RepairTask is a specific implementation of Task that handles repair operations.
    """

    @override
    def initialize(self):
        """
        Initialize the repair task.
        This method should be called before running the task.
        """

        self._instance = Instance(
            source=pathlib.Path(self._config.path),
            mode="build",
        )

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._loop_thread.start()

        with open(
            PROJECT_ROOT / "afixl" / "backend" / "repair" / "prompts" / "system.txt",
            "r",
        ) as f:
            sys_prompt = f.read()

        self._source_structure = self._get_source_structure("/src")
        self._llm_agent = Agent(
            "google-gla:gemini-2.0-flash",
            output_type=ProposedPatch | RequestCode | MakeNote,
            system_prompt=sys_prompt,
        )
        self._output_handle = None
        self._fixing_crash: Crash | None = None

    @override
    def close(self):
        """
        Close the repair task and perform any necessary cleanup.
        This method should be called when the task is no longer needed.
        """
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._loop_thread.join()
            self._loop.close()

        if self._instance:
            self._instance.close()
            self._instance = None

    @override
    def run(self):
        """
        Run the repair task.
        This method should contain the logic for executing the repair process.
        """
        crashes = self._crash_repository.get_crashes(
            lambda c: c.stage == "replay" and c.reproducable is True and c.retry_count < 20
        )

        if crashes and not self._output_handle:
            self._fixing_crash = crashes[0]
            logger.info(f"Repairing crash {self._fixing_crash.id}")

            with open(
                PROJECT_ROOT / "afixl" / "backend" / "repair" / "prompts" / "user.txt",
                "r",
            ) as f:
                user_prompt = f.read()
                prompt = user_prompt.format(
                    crash_report=self._fixing_crash.report.decode("utf-8"),
                    code_structure=self._source_structure,
                    requested_code="\n\n".join(
                        f"File: {path}\n{content.decode('utf-8')}"
                        for path, content in self._fixing_crash.requested_content.items()
                    ),
                    notes="\n".join(self._fixing_crash.note),
                )
            self._output_handle = self._request_llm(prompt)

        if self._output_handle and self._output_handle.done():
            try:
                operation = self._output_handle.result().output
                self._do_operation(operation)
            except Exception as e:
                logger.error(f"LLM request failed: {e}")
            self._output_handle = None
            self._fixing_crash = None

    def _request_llm(self, prompt: str):
        return asyncio.run_coroutine_threadsafe(self._llm_agent.run(prompt), self._loop)

    def _get_source_structure(self, path: str) -> str:
        if not self._instance:
            raise ValueError("Instance is not set.")

        install_handle = self._instance.execute(
            command="apt-get install -y tree",
        )
        while install_handle.running:
            pass

        if install_handle.exit_code != 0:
            raise RuntimeError("Failed to install 'tree' command.")

        handle = self._instance.execute(
            command="tree",
            workdir=path,
            environment=self._config.environment.runtime,
        )

        while handle.running:
            pass

        if handle.exit_code != 0:
            raise RuntimeError("Failed to get source structure.")

        return f"path: {path}\n{handle.output.decode('utf-8')}"

    def _get_file_content(self, file_path: str, raw: bool = False) -> str:
        """
        Read and return the content of a file.
        Args:
            file_path (str): The path to the file.
        Returns:
            str: The content of the file.
        """

        if not self._instance:
            raise ValueError("Instance is not set.")

        tar_bytes = self._instance.read(file_path)
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

    def _do_operation(self, operation: RequestCode | ProposedPatch | MakeNote):
        self._fixing_crash.retry_count += 1
        self._fixing_crash.history.append(operation)
        if isinstance(operation, RequestCode):
            self._fixing_crash.requested_content[operation.file] = (
                self._get_file_content(operation.file).encode("utf-8")
            )
            logger.info(f"Crash {self._fixing_crash.id} requested code {operation.file}")
        elif isinstance(operation, ProposedPatch):
            self._fixing_crash.stage = "repair"
            logger.info(f"Crash {self._fixing_crash.id} proposed a patch")
        elif isinstance(operation, MakeNote):
            self._fixing_crash.note.append(operation.content)
            logger.info(f"Crash {self._fixing_crash.id} made a note")
        else:
            raise ValueError(f"Unknown operation type: {type(operation)}")
        self._crash_repository.update_crash(self._fixing_crash)
