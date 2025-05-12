import docker
import uuid
import logging
import io
import tarfile


class Engine:
    """
    A wrapper class for Docker to run commands in a containerized environment.
    """

    def __init__(self, image_dir: str, no_cache: bool = False):
        """
        Initialize the Engine with the given image directory.

        Args:
            image_dir (str): The directory containing the Dockerfile and other files for building the image.
        """
        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Initialize Docker client and build the image
        self.logger.debug(f"Building Docker image from {image_dir}, no cache: {no_cache}")
        self.docker_client = docker.from_env()
        self.image_dir = image_dir
        self.image_name = f"{uuid.uuid4()}"
        self.logger.debug(f"Image directory: {self.image_dir}")
        self.logger.debug(f"Building image with tag {self.image_name}.")
        self.docker_client.images.build(path=self.image_dir, tag=self.image_name, nocache=no_cache)
        self.container = self.docker_client.containers.run(
            self.image_name, detach=True, tty=True
        )
        self.logger.debug(
            f"Container {self.container.id} started from image {self.image_name}."
        )

    def __del__(self):
        """
        Clean up the Docker container when the Engine instance is deleted.
        """
        self.logger.debug(f"Removing container {self.container.id}.")
        self.container.remove(force=True)
        self.logger.debug(f"Container {self.container.id} removed.")
        self.docker_client.images.remove(self.image_name, force=True)
        self.logger.debug(f"Image {self.image_name} removed.")

    def run_command(
        self, command: str, workdir: str = None, env: dict = None, timeout: int = -1
    ) -> tuple:
        """
        Run a command in the Docker container and return the exit code and output.

        Args:
            command (str): The command to run.
            workdir (str, optional): The working directory inside the container. Defaults to None.
            env (dict, optional): Environment variables to set in the container. Defaults to None.
            timeout (int, optional): Timeout for the command in seconds. Defaults to -1 (no timeout).

        Returns:
            tuple: A tuple containing the exit code and output string of the command.
        """
        if timeout > 0:
            self.logger.debug(f"Setting timeout to {timeout} seconds.")
            command = f"timeout {timeout}s {command}"
        self.logger.debug(f"Running command: {command}")
        exit_code, output_str = self.container.exec_run(
            command,
            workdir=workdir,
            environment=env,
        )
        self.logger.debug(f"Command output: {output_str}")
        self.logger.debug(f"Command exited with code: {exit_code}")
        return exit_code, output_str

    def check_directory(self, directory: str) -> bool:
        """
        Check if a directory exists in the Docker container.

        Args:
            directory (str): The directory to check.

        Returns:
            bool: True if the directory exists, False otherwise.
        """
        self.logger.debug(f"Checking if directory {directory} exists.")
        exit_code, _ = self.run_command(f'test -d "{directory}"')
        if exit_code != 0:
            self.logger.debug(f"Directory {directory} does not exist.")
            return False
        self.logger.debug(f"Directory {directory} exists.")
        return True

    def check_file(self, file_path: str) -> bool:
        """
        Check if a file exists in the Docker container.

        Args:
            file_path (str): The path to the file to check.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        self.logger.debug(f"Checking if file {file_path} exists.")
        exit_code, _ = self.run_command(f'test -f "{file_path}"')
        if exit_code == 0:
            self.logger.debug(f"File {file_path} exists.")
            return True
        self.logger.debug(f"File {file_path} does not exist.")
        return False

    def get_files(self, directory: str) -> dict:
        """
        Get the list of files in a directory in the Docker container.

        Args:
            directory (str): The directory to list files from.

        Returns:
            dict: A dictionary containing the file names as keys and their contents as values.
        """

        self.logger.debug(f"Getting files from directory {directory} in the container.")
        files_content = {}

        # Check if the directory exists
        if not self.check_directory(directory):
            self.logger.warning(
                f"Directory {directory} does not exist in the container."
            )
            return files_content

        # List files in the directory
        list_files_cmd = 'find . -maxdepth 1 -type f -printf "%f\\0"'
        exit_code, output = self.run_command(list_files_cmd, workdir=directory)

        # Check if the command was successful
        if exit_code != 0:
            self.logger.error(
                f"Failed to list files in {directory}. Error: {output.decode(errors='ignore')}"
            )
            return {}

        # Decode the output and split by null character
        file_names = [
            name
            for name in output.decode("utf-8", errors="replace").split("\0")
            if name
        ]

        # Check if any files were found
        if not file_names:
            self.logger.debug(f"No files found in directory {directory}.")
            return files_content

        # Read the content of each file
        for file_name in file_names:
            read_file_cmd = f'cat "{file_name}"'
            exit_code, content = self.run_command(read_file_cmd, workdir=directory)

            # Check if the command was successful
            if exit_code == 0:
                files_content[file_name] = content.decode("utf-8", errors="replace")
            else:
                self.logger.warning(
                    f"Failed to read content of file {file_name} in {directory}. "
                    f"Cat command exited with {exit_code}. Output: {content.decode(errors='ignore')}"
                )

        self.logger.debug(
            f"Successfully retrieved {len(files_content)} files from {directory}."
        )
        return files_content
    
    def write_file(self, file_path: str, content: str) -> bool:
        """
        Write content to a file in the Docker container.

        Args:
            file_path (str): The path to the file to write to.
            content (str): The content to write to the file.

        Returns:
            bool: True if the write operation was successful, False otherwise.
        """
        self.logger.debug(f"Writing content to file {file_path}.")

        # Create a tar stream to write the file
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            file_info = tarfile.TarInfo(name=file_path)
            file_info.size = len(content)
            file_info.mode = 0o644
            tar.addfile(file_info, io.BytesIO(content.encode('utf-8')))
        tar_stream.seek(0)
        self.logger.debug(f"Tar stream created for file {file_path}.")

        # Copy the tar stream to the container
        if self.container.put_archive(path='/', data=tar_stream.read()):
            self.logger.debug(f"File {file_path} written successfully.")
            return True
        self.logger.error(f"Failed to write file {file_path}.")
        return False
