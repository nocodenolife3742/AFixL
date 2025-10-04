import docker


class ExecHandle:
    """
    A class representing a handle to an executed command in a Docker container.
    This class provides methods to check the status of the command and, once
    completed, retrieve its exit code and output.
    """

    def __init__(self, client: docker.DockerClient, exec_id: str):
        """
        Initialize an ExecHandle instance.

        Args:
            client (docker.DockerClient): The Docker client instance.
            exec_id (str): The ID of the executed command.
        """
        # Initialize the Docker client and exec ID.
        self._client = client
        self._exec_id = exec_id

        # Create a stream to the executed command.
        self._stream = self._client.api.exec_start(exec_id, stream=True)

        # Internal caches for the results
        self._running = True
        self._output = None
        self._exit_code = None

    def _fetch_results(self):
        """
        Fetch the results of the executed command.
        """
        # If the command is already completed, do nothing.
        if not self._running:
            return

        # Update the running status.
        inspection = self._client.api.exec_inspect(self._exec_id)
        self._running = inspection["Running"]

        # If the command is not running, fetch the exit code and output.
        if not self._running:
            self._exit_code = inspection["ExitCode"]
            self._output = b"".join(self._stream)

    @property
    def running(self) -> bool:
        """
        Check if the command is still running.

        Returns:
            bool: True if the command is running, False otherwise.
        """
        # Fetch the results to update the running status.
        self._fetch_results()

        return self._running

    @property
    def exit_code(self) -> int | None:
        """
        Get the exit code of the executed command.

        Returns:
            int | None: The exit code of the command if it has completed, None otherwise.
        """
        # Fetch the results to update the exit code.
        self._fetch_results()

        return self._exit_code

    @property
    def output(self) -> bytes | None:
        """
        Get the output of the executed command.

        Returns:
            bytes | None: The output of the command if it has completed, None otherwise.
        """
        # Fetch the results to update the output.
        self._fetch_results()

        return self._output
