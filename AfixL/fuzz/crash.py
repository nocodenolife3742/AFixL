from enum import Enum
from dataclasses import dataclass


class CrashType(Enum):
    """
    Enum to represent the type of crash.
    """

    NOT_TESTED = 0
    UNKNOWN = 1
    REPRODUCIBLE = 2
    NON_REPRODUCIBLE = 3
    TIMEOUT = 4


class Crash:
    """
    This class is used to represent a crash in the fuzzing process.
    It contains the crash report and provides methods to access it.
    """

    def __init__(
        self,
        input_file: str,
        input_content: str,
        type: CrashType = CrashType.NOT_TESTED,
        replay_result: str = "",
        fixed: bool = False,
        fixed_content: dict[str, str] = {},
    ):
        """
        Initialize the Crash object with the input file and its content.

        Args:
            input_file (str): The name of the input file that caused the crash.
            input_content (str): The content of the input file that caused the crash.
            reproducible (CrashType): The reproducibility status of the crash.
            replay_result (str | None): The result of the replay attempt.
            fixed (bool): Whether the crash has been fixed or not.
            fixed_content (dict[str, str]): Diff files between the fixed and unfixed versions of the code.
        """
        self.input_file = input_file
        self.input_content = input_content
        self.type = type
        self.replay_result = replay_result
        self.fixed = fixed
        self.fixed_content = fixed_content

    def __eq__(self, other):
        """
        Check if two Crash objects are equal based on their input file and content.

        Args:
            other (Crash): The other Crash object to compare with.

        Returns:
            bool: True if the input file and content are the same, False otherwise.
        """
        return (
            self.input_file == other.input_file
            and self.input_content == other.input_content
        )
    
    def __repr__(self):
        """
        Return a string representation of the Crash object.

        Returns:
            str: A string representation of the Crash object.
        """
        return f"Crash(input_file={self.input_file}, type={self.type}, fixed={self.fixed})"
