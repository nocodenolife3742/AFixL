from typing import override
import logging
import sqlite3

from afixl.backend.task import Task
from afixl.orchestration.models import Crash


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
        # read crashes from crash.db
        connection = sqlite3.connect("data/crash.db")
        cursor = connection.cursor()
        cursor.execute(
            "SELECT localId, fix_commit, repo_addr, crash_output, project FROM crash WHERE localId = 42471383"
        )

        # upload crashes to the crash repository
        rows = cursor.fetchall()
        logger.info("Reading crashes from database.")
        for local_id, fix_commit, repo_addr, crash_output, project in rows:
            crash = Crash(
                id=str(local_id),
                stage="replay",
                report=crash_output.encode("utf-8"),
                fix_commit=fix_commit,
                repo_addr=repo_addr,
                project=project,
            )
            self._crash_repository.add_crash(crash)
        connection.close()

    @override
    def close(self):
        """
        Close the replay task and perform any necessary cleanup.
        This method should be called when the task is no longer needed.
        """
        pass

    @override
    def run(self):
        """
        Run the replay task.
        This method should contain the logic for executing the replay process.
        """
        pass
