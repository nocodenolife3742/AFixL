import logging
from typing import Callable

from afixl.orchestration.models import Crash


logger = logging.getLogger(__name__)


class CrashRepository:
    """
    Repository for managing crash data.
    """

    def __init__(self):
        """
        Initialize the CrashRepository.
        """
        # Initialize the crashes list
        self._crashes = []

    def add_crash(self, crash: Crash):
        """
        Add a crash to the repository.

        Args:
            crash (Crash): The crash instance to add.

        Example:
            >>> crash = Crash(stage="fuzz", sanitizer="address", input=b"input")
            >>> repository.add_crash(crash)
            >>> print(repository.get_crashes())
        """
        # Check if the crash is already in the list
        if any(existing_crash.id == crash.id for existing_crash in self._crashes):
            logger.warning(f"Crash with ID {crash.id} already exists.")
            return

        # Add the crash to the list
        self._crashes.append(crash)

    def get_crashes(self, filter: Callable[[Crash], bool] = None):
        """
        Get the list of crashes managed by the

        Args:
            filter (Callable[[Crash], bool], optional): A filter function to apply to the crashes.
                If provided, only crashes that match the filter will be returned.

        Returns:
            list[Crash]: The list of crashes, optionally filtered.

        Example:
            >>> crashes = repository.get_crashes()
            >>> print(crashes)
        """
        # If a filter is provided, apply it to the crashes list
        if filter:
            return [crash for crash in self._crashes if filter(crash)]

        # Otherwise, return the full list of crashes
        return self._crashes

    def update_crash(self, crash: Crash):
        """
        Update an existing crash in the Manager's list of crashes.

        Args:
            crash (Crash): The crash instance to update.

        Example:
            >>> crash = await manager.get_crashes()[0]
            >>> crash.stage = "replay"
            >>> await manager.update_crash(crash)
        """
        # Find the crash by ID and update it
        for i, existing_crash in enumerate(self._crashes):
            if existing_crash.id == crash.id:
                self._crashes[i] = crash
                return

        # If the crash was not found, log a warning
        logger.warning(f"Crash with ID {crash.id} not found for update.")
