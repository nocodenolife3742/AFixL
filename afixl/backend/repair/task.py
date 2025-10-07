from typing import override
import logging
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
import asyncio
import threading
import tarfile

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

TIMES_THRESHOLD = 15  # Number of retries before giving up on a crash


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
        self._instance: Instance = None

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._loop_thread.start()

        with open(
            PROJECT_ROOT / "afixl" / "backend" / "repair" / "prompts" / "system.txt",
            "r",
        ) as f:
            sys_prompt = f.read()

        self._llm_agent = Agent(
            GoogleModel("gemini-2.5-flash"),
            output_type=ProposedPatch | RequestCode | MakeNote,
            system_prompt=sys_prompt,
            model_settings=GoogleModelSettings(
                google_thinking_config={"thinking_budget": 1000},
            ),
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
            lambda c: c.stage == "replay" and c.retry_count < TIMES_THRESHOLD
        )

        if crashes and not self._output_handle:
            self._fixing_crash = crashes[0]
            logger.info(f"Repairing crash {self._fixing_crash.id}")
            self._instance = Instance(
                source=f"n132/arvo:{self._fixing_crash.id}-vul", mode="pull"
            )

            with open(
                PROJECT_ROOT / "afixl" / "backend" / "repair" / "prompts" / "user.txt",
                "r",
            ) as f:
                user_prompt = f.read()

                requested_code = ""
                for file, content in self._fixing_crash.requested_content.items():
                    requested_code += f"- File: {file}\n"
                    last = 0
                    for line_num in sorted(content.keys()):
                        if line_num > last + 1:
                            requested_code += "...\n"
                        requested_code += (
                            content[line_num] + "\n"
                            if content[line_num].strip()
                            else "<No Content>\n"
                        )
                        last = line_num
                    requested_code += "\n\n"
                prompt = user_prompt.format(
                    crash_report=self._fixing_crash.report.decode("utf-8"),
                    requested_code=requested_code.strip() or "None",
                    notes="\n".join(self._fixing_crash.note) or "None",
                )
            self._output_handle = self._request_llm(prompt)

        if self._output_handle and self._output_handle.done():
            try:
                operation = self._output_handle.result().output
                self._do_operation(operation)
            except Exception as e:
                logger.error(
                    f"LLM request failed for crash {self._fixing_crash.id}: {e}"
                )
            self._output_handle = None
            self._fixing_crash = None
            self._instance.close()
            self._instance = None

    def _request_llm(self, prompt: str):
        return asyncio.run_coroutine_threadsafe(
            self._llm_agent.run(prompt),
            self._loop,
        )

    def _get_file_content(self, file_path: str, line_limit: int) -> dict[int, str]:
        """
        Read and return the content of a file.
        Args:
            file_path (str): The path to the file.
            line_limit (int): The line number to retrieve (1-based). If -1, retrieve the entire file.
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
                    raw_content += "\n<End of File>"
                    content = {
                        i + 1: f"line {i + 1:4d} : {line}"
                        for i, line in enumerate(raw_content.splitlines())
                        if (i + 1 >= line_limit - 30 and i + 1 < line_limit + 30)
                        or line == "<End of File>"
                    }
                    return {k: v for k, v in content.items()}

                else:
                    raise ValueError(
                        f"Could not extract file from tar archive: {file_path}"
                    )

    def _do_operation(self, operation: RequestCode | ProposedPatch | MakeNote):
        self._fixing_crash.history.append(operation)
        if isinstance(operation, RequestCode):

            if (
                operation.file in self._fixing_crash.requested_content.keys()
                and operation.line
                in self._fixing_crash.requested_content[operation.file].keys()
            ):
                logger.warning(
                    f"Crash {self._fixing_crash.id} made a redundant code request for {operation.file} at line {operation.line}"
                )
            else:
                try:
                    new_content = self._get_file_content(operation.file, operation.line)
                    if operation.file not in self._fixing_crash.requested_content:
                        self._fixing_crash.requested_content[operation.file] = {}
                    self._fixing_crash.requested_content[operation.file].update(
                        new_content
                    )
                    self._fixing_crash.note.append(
                        f"Reason for requesting line {operation.line} of {operation.file}: {operation.reason}"
                    )
                    logger.info(
                        f"Crash {self._fixing_crash.id} requested code {operation.file} at line {operation.line}"
                    )
                except Exception as e:
                    logger.info(
                        f"LLM failed to get requested code {operation.file} at line {operation.line} for crash {self._fixing_crash.id}"
                    )
        elif isinstance(operation, ProposedPatch):
            self._fixing_crash.stage = "repair"
            logger.info(f"Crash {self._fixing_crash.id} proposed a patch")
        elif isinstance(operation, MakeNote):
            self._fixing_crash.note.append(operation.content)
            logger.info(f"Crash {self._fixing_crash.id} made a note")
        else:
            raise ValueError(f"Unknown operation type: {type(operation)}")
        self._crash_repository.update_crash(self._fixing_crash)

        # Save the crash to a file for record-keeping
        record_file = PROJECT_ROOT / "records" / f"{self._fixing_crash.id}.json"
        record_file.parent.mkdir(parents=True, exist_ok=True)
        with open(record_file, "w") as f:
            json = self._fixing_crash.model_dump_json(
                indent=2, exclude={"retry_count", "requested_content", "report"}
            )
            f.write(json)
        self._fixing_crash.retry_count += 1
