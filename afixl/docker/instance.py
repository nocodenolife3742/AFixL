import io
import logging
from pathlib import Path
import docker
import docker.models.images

from afixl.docker.exec_handle import ExecHandle

logger = logging.getLogger(__name__)


class Instance:
    """
    A class representing a Docker container instance.
    """

    def __init__(
        self,
        source: str,
        mode: str,
        client: docker.DockerClient = docker.from_env(),
        no_cache: bool = False,
    ):
        """
        Initialize an Instance for managing a Docker container.

        Args:
            source (str): If mode is "pull", the Docker image name (e.g., "ubuntu:latest").
                  If mode is "build", the path to the directory containing the Dockerfile.
            mode (str): "pull" to pull an image from a registry, or "build" to build from a local path.
            client (docker.DockerClient, optional): Docker client to use. Defaults to docker.from_env().
            no_cache (bool, optional): If True, disables Docker build cache when building an image.
                This is only applicable when mode is "build".

        Raises:
            ValueError: If the mode is not "pull" or "build".
            FileNotFoundError: If the specified path does not exist when building an image.
            NotADirectoryError: If the specified path is not a directory when building an image.

        Example:
            >>> with Instance("ubuntu:latest", "pull") as instance:
            ...     print("Docker container is running.")
        """
        # Check the mode
        if mode not in ("pull", "build"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'pull' or 'build'.")

        # Initialize the Docker client
        self._client = client

        # Run the Docker container based on the specified mode
        match mode:
            case "pull":
                image = self._pull_image(source)
            case "build":
                image = self._build_image(source, no_cache=no_cache)
            case _:
                raise ValueError(f"Invalid mode: {mode}. Must be 'pull' or 'build'.")

        # Run the Docker container
        logger.debug(f"Running Docker container from image: {image.short_id}")
        self._container = self._client.containers.run(
            image,
            detach=True,
            tty=True,
        )

    def __enter__(self):
        """
        Enter the context of the Instance.

        Returns:
            Instance: The current instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context of the Instance and clean up the container.

        Args:
            exc_type: The exception type.
            exc_val: The exception value.
            exc_tb: The traceback object.
        """
        # Close the instance, which stops and removes the container
        self.close()

    def close(self):
        """
        Close the Instance and clean up the container.

        This method stops and removes the Docker container associated with this instance.
        It should be called to ensure proper cleanup of resources when the instance is no longer needed.
        Example:
            >>> instance = Instance("ubuntu:latest", "pull")
            >>> instance.close()
        """
        # Check if the Docker client is available and connected
        if not self._client or not self._client.ping():
            logger.warning("Docker client is not available or not connected.")
            return

        # Check if the container exists
        if not self._container or not self._container.id:
            logger.warning("No container to close.")
            return

        # Stop and remove the container
        self._container.stop(timeout=0)
        self._container.remove(force=True)
        logger.debug(f"Container {self._container.short_id} stopped and removed.")

    def _pull_image(self, image_name: str) -> docker.models.images.Image:
        """
        Pull a Docker image from a registry.

        Args:
            image_name (str): The name of the Docker image to pull (e.g., "ubuntu:latest").

        Returns:
            docker.models.images.Image: The pulled Docker image.
        """
        # Pull the Docker image
        logger.debug(f"Pulling Docker image: {image_name}")
        image = self._client.images.pull(image_name)
        logger.debug(f"Image pulled successfully. Image ID: {image.short_id}")

        return image

    def _build_image(
        self, path: str, no_cache: bool = False
    ) -> docker.models.images.Image:
        """
        Build a Docker image from a local path.

        Args:
            path (str): The path to the directory containing the Dockerfile.
            no_cache (bool, optional): If True, disables Docker build cache.

        Returns:
            docker.models.images.Image: The built Docker image.

        Raises:
            ValueError: If the specified path is not an absolute path.
            FileNotFoundError: If the specified path does not exist.
            NotADirectoryError: If the specified path is not a directory.
        """
        # Check if the path is absolute and exists
        path = Path(path)
        if not path.is_absolute():
            raise ValueError(f"Path {path} must be an absolute path.")
        if not path.exists():
            raise FileNotFoundError(f"Path {path} does not exist.")
        if not path.is_dir():
            raise NotADirectoryError(f"Path {path} is not a directory.")

        # Build the Docker image
        logger.debug(f"Building Docker image from path: {path}")
        image, _ = self._client.images.build(
            path=str(path),
            rm=True,
            nocache=no_cache,
        )
        logger.debug(f"Image built successfully. Image ID: {image.short_id}")

        return image

    def execute(
        self,
        command: str,
        workdir: str = None,
        environment: dict = None,
    ) -> ExecHandle:
        """
        Execute a command inside the Docker container in detached mode.

        Args:
            command (str): The command to execute inside the container.
            workdir (str, optional): The working directory inside the container.
            environment (dict, optional): Environment variables to set in the container.

        Returns:
            ExecHandle: An instance of ExecHandle that provides access to the command's output and status.

        Example:
            >>> with Instance("ubuntu:latest", "pull") as instance:
            ...     handle = instance.execute(
            ...         "echo 'Hello, World!'",
            ...         workdir="/tmp",
            ...         environment={"MY_ENV_VAR": "value"}
            ...     )
            ...     print(f"Running: {handle.running}")
            ...     print(f"Exit Code: {handle.exit_code}")
            ...     print(f"Stdout: {handle.stdout.decode()}")
            ...     print(f"Stderr: {handle.stderr.decode()}")
        """
        # Execute the command
        logger.debug(
            f"Executing command: {command} in container {self._container.short_id}"
        )
        exec_id = self._client.api.exec_create(
            self._container.id,
            command,
            workdir=workdir,
            environment=environment,
            tty=True,
        )["Id"]
        return ExecHandle(self._client, exec_id)

    def read(self, path: str) -> io.BytesIO:
        """
        Read a file or directory from the container.

        Args:
            path (str): The path to the file or directory to read from the container.

        Returns:
            BytesIO: An in-memory bytes buffer containing the tar archive of the specified file or directory.

        Raises:
            ValueError: If the specified path is not an absolute path.
            FileNotFoundError: If the specified path does not exist in the container.

        Example:
            >>> with Instance("example") as instance:
            ...     bytes = instance.read("/path/to/file.txt")
            ...     with tarfile.open(fileobj=bytes, mode="r|*") as tar:
            ...         tar.extractall(path="output_directory", filter="data")
        """
        # Check if the path is absolute
        path = Path(path).as_posix()
        if not path.startswith("/"):
            raise ValueError(f"Path {path} must be an absolute path.")

        # Check if the path exists in the container
        exit_code, _ = self._container.exec_run(f"test -e {path}")
        if exit_code != 0:
            raise FileNotFoundError(f"Path {path} does not exist in the container.")

        # Read the tar stream from the container
        logger.debug(f"Reading path: {path}")
        stream, _ = self._container.get_archive(path)
        tar_bytes = b"".join(stream)
        return io.BytesIO(tar_bytes)

    def write(self, path: str, data: io.BytesIO) -> bool:
        """
        Write a file or directory to the container.

        Args:
            path (str): The path in the container where the tar archive will be written.
            data (io.BytesIO): An in-memory bytes buffer containing the tar archive to write.

        Returns:
            bool: True if the write operation was successful, False otherwise.

        Raises:
            ValueError: If the specified path is not an absolute path.
            FileNotFoundError: If the specified path does not exist in the container.

        Example:
            >>> with Instance("example") as instance:
            ...     with open("file.tar", "rb") as f:
            ...         instance.write("/path/to/destination", io.BytesIO(f.read()))
        """
        # Check if the path is absolute
        path = Path(path).as_posix()
        if not path.startswith("/"):
            raise ValueError(f"Path {path} must be an absolute path.")

        # Check if the path exists in the container
        exit_code, _ = self._container.exec_run(f"test -d {path}")
        if exit_code != 0:
            raise NotADirectoryError(
                f"Path {path} is not a directory in the container."
            )

        # Write the tar stream to the container
        logger.debug(f"Writing to path: {path}")
        data.seek(0)
        return self._container.put_archive(path, data.read())
