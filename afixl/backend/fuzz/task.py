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
        pass

    @override
    def close(self):
        """
        Close the fuzzing task and perform any necessary cleanup.
        This method should be called when the task is no longer needed.
        """
        pass

    @override
    def run(self):
        """
        Run the fuzzing task.
        This method should contain the logic for executing the fuzzing process.
        """
        pass
