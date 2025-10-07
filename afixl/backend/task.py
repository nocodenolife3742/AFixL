from abc import ABC, abstractmethod

from afixl.orchestration.crash import CrashRepository


class Task(ABC):
    """
    Abstract base class for tasks.
    """

    def __init__(self, repository: CrashRepository, name: str):
        """
        Initialize the Task with a reference to the CrashRepository and a name.

        Args:
            repository (CrashRepository): The CrashRepository instance to manage the task.
            name (str): The name of the task.
        """
        # Initialize the Task with the given repository and name
        self._crash_repository = repository
        self._name = name

    def __enter__(self):
        """
        Enter the context of the Task.
        Initializes the task when entering the context.
        """
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context of the Instance and clean up the container.

        Args:
            exc_type: The exception type.
            exc_val: The exception value.
            exc_tb: The traceback object.
        """
        self.close()

    @abstractmethod
    def initialize(self):
        """
        Initialize the task.
        This method should be called before running the task.
        """
        pass

    @abstractmethod
    def close(self):
        """
        Close the task and perform any necessary cleanup.
        This method should be called when the task is no longer needed.
        """
        pass

    @abstractmethod
    def run(self):
        """
        Abstract method to run the task.
        This method should be implemented by subclasses to define the task's behavior.
        """
        pass
