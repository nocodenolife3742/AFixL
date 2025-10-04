from pathlib import Path
import tomllib
from pydantic import ValidationError
import logging

from afixl.orchestration.models import Config

logger = logging.getLogger(__name__)


class Target:
    """
    Represents a target directory for orchestration tasks.
    """

    def __init__(self, path: Path):
        """
        Initialize the Target with the path to the target directory.

        Args:
            path (Path): The path to the target directory.
        """
        # Validate the target folder structure
        self._path = Path(path).resolve()
        self._validate_structure(self._path)
        self._config = self._load_config()

    def _validate_structure(self, path: Path):
        """
        Validate the target folder structure.

        Raises:
            FileNotFoundError: If a required file is missing.
            NotADirectoryError: If a required directory is missing or not a directory.
            ValueError: If a required directory is empty.
        """
        # Check if the target directory is valid
        if not path.exists() or not path.is_dir():
            raise NotADirectoryError(f"Target path {path} is not a valid directory.")

        # Check if the required files and directories exist in the target directory
        required_files = ["config.toml", "build.sh", "Dockerfile"]
        for file in required_files:
            file_path = path / file
            if not file_path.exists() or not file_path.is_file():
                raise FileNotFoundError(f"Required file {file_path} is missing.")

        # Check if the required directories exist and are not empty
        required_dirs = ["src", "eval"]
        for dir in required_dirs:
            dir_path = path / dir
            if not dir_path.exists() or not dir_path.is_dir():
                raise NotADirectoryError(f"Required directory {dir_path} is missing.")
            if not any(dir_path.iterdir()):
                raise ValueError(f"Required directory {dir_path} is empty.")

        # Check if the eval directory only contains files
        for item in (path / "eval").iterdir():
            if not item.is_file():
                raise ValueError(
                    f"Eval directory {path / 'eval'} must only contain files, found: {item}"
                )

    def _load_config(self) -> Config:
        """
        Load the configuration from a TOML file in the target directory.

        Returns:
            Config: The loaded configuration object.

        Raises:
            FileNotFoundError: If the configuration file does not exist.
            NotADirectoryError: If the configuration path is not a file.
            ValidationError: If the configuration is invalid.
        """
        # Load the configuration file using tomllib
        config_path = self._path / "config.toml"
        with open(config_path, "rb") as f:
            try:
                config_data = tomllib.load(f)
                return Config(**config_data)
            except ValidationError as e:
                raise ValidationError(
                    f"Invalid configuration in {config_path}: {e}"
                ) from e

    @property
    def config(self) -> Config:
        """
        Get the configuration for the target.

        Returns:
            Config: The configuration object for the target.
        """
        return self._config

    @property
    def source(self) -> Path:
        """
        Get the path to the source code directory.

        Returns:
            Path: The path to the source code directory.
        """
        return self._path / "src"

    @property
    def eval_paths(self) -> list[Path]:
        """
        Get the paths to the evaluation tests.

        Returns:
            list[Path]: A list of paths to the evaluation tests.
        """
        return [
            item.resolve() for item in (self._path / "eval").iterdir() if item.is_file()
        ]
    
    @property
    def dockerfile(self) -> Path:
        """
        Get the path to the Dockerfile.

        Returns:
            Path: The path to the Dockerfile.
        """
        return self._path / "Dockerfile"
    
    @property
    def build_script(self) -> Path:
        """
        Get the path to the build script.

        Returns:
            Path: The path to the build script.
        """
        return self._path / "build.sh"
