from AfixL.engine import Engine
from AfixL.fuzz.crash import Crash, CrashType
import logging

logger = logging.getLogger(__name__)


REPLAY_TIMEOUT = 60  # seconds


def build(engine: Engine, mode: str, config: dict) -> bool:
    """
    Build the targets using the specified build command and mode.

    Args:
        engine (Engine): The Engine instance to use for building.
        mode (str): The build mode (e.g., "fuzz", "replay").
        config (dict): The configuration dictionary containing build settings.

    Returns:
        bool: True if the build was successful, False otherwise.
    """

    # Check if the mode is valid
    if mode not in ["fuzz", "replay"]:
        logger.error("Invalid mode. Use 'fuzz' or 'replay'.")
        raise ValueError("Invalid mode. Use 'fuzz' or 'replay'.")

    # Set the environment variables based on the mode
    env = config["environment"].copy()
    if mode == "fuzz":
        env["CXX"] = "afl-clang-fast++"
        env["CC"] = "afl-clang-fast"
        env["CXXFLAGS"] = "-Wall -Wextra"
        env["CFLAGS"] = "-Wall -Wextra"
        env["LD"] = "afl-clang-fast"
        env["AFL_USE_ASAN"] = "1"
        env["AFL_USE_UBSAN"] = "1"
    if mode == "replay":
        env["CXX"] = "g++"
        env["CC"] = "gcc"
        env["CXXFLAGS"] = "-Wall -Wextra -fsanitize=address,undefined -g"
        env["CFLAGS"] = "-Wall -Wextra -fsanitize=address,undefined -g"
        env["LD"] = "g++"
        env["ASAN_OPTIONS"] = "log_path=/out/asan.log"
        env["UBSAN_OPTIONS"] = "log_path=/out/ubsan.log"

    # Build the targets using the specified build command
    logger.debug("Building targets...")
    logger.debug(f"Build command: {config['project']['build']}")
    logger.debug(f"Environment: {env}")
    logger.debug(f"Working directory: {config['project']['directory']}")
    exit_code, output_bytes = engine.run_command(
        config["project"]["build"],
        workdir=config["project"]["directory"],
        env=env,
    )

    # Check the exit code to determine if the build was successful
    if exit_code != 0:
        logger.error(f"Build failed with exit code {exit_code}.")
        logger.error(f"Output: {output_bytes.decode('utf-8')}")
        return False
    logger.debug("Build completed successfully.")
    logger.debug(f"Output: {output_bytes.decode('utf-8')}")
    return True


def fuzz(engine: Engine, config: dict, timeout: int = 60) -> bool:
    """
    Run the fuzzing process using the specified configuration.

    Args:
        engine (Engine): The Engine instance to use for fuzzing.
        config (dict): The configuration dictionary containing fuzz settings.
        timeout (int): The timeout for the fuzzing process in seconds.

    Returns:
        bool: True if the fuzzing process was successful, False otherwise.
    """
    # Set the environment variables for fuzzing
    env = config["environment"].copy()
    env["AFL_USE_ASAN"] = "1"
    env["AFL_USE_UBSAN"] = "1"

    # Check if the /out/default directory exists
    if engine.check_directory("/out/default"):
        logger.debug("Resuming fuzzing from previous run...")
        resume = True
    else:
        logger.debug("Starting a new fuzzing run...")
        resume = False

    # Run the fuzzing process using the specified command
    seeds = config["project"]["seeds"]
    command = config["project"]["command"]
    fuzz_command = (
        f"afl-fuzz -i {'-' if resume else seeds} -o /out -V {timeout} -- {command}"
    )
    logger.debug(f"Fuzzing command: {fuzz_command}")
    logger.debug(f"Environment: {env}")
    logger.debug(f"Working directory: {config['project']['directory']}")
    logger.debug(f"Timeout: {timeout} seconds")
    exit_code, output_str = engine.run_command(
        fuzz_command,
        workdir=config["project"]["directory"],
        env=env,
    )

    # Check the exit code to determine if the fuzzing process was successful
    if exit_code != 0:
        logger.error(f"Fuzzing failed with exit code {exit_code}.")
        logger.error(f"Output: {output_str}")
        return False
    logger.debug("Fuzzing completed successfully.")
    logger.debug(f"Output: {output_str}")
    return True


def replay(engine: Engine, crash: Crash, config: dict) -> Crash:
    """
    Replay the fuzzing results using the specified configuration.

    Args:
        engine (Engine): The Engine instance to use for replaying.
        crash (Crash): The Crash object containing the crash information.
        config (dict): The configuration dictionary containing replay settings.

    Returns:
        Crash: The updated Crash object with the replay result.
    """
    if crash.type != CrashType.NOT_TESTED:
        logger.debug("Crash already tested. Skipping replay.")
        return crash
    replay_result = ""
    type = crash.type

    # Set the environment variables for replaying
    env = config["environment"].copy()
    env["ASAN_OPTIONS"] = "log_path=/out/asan.log"
    env["UBSAN_OPTIONS"] = "log_path=/out/ubsan.log"

    # Create the file for the crash input
    status = engine.write_file(
        f"/tmp/{crash.input_file}",
        crash.input_content,
    )
    if not status:
        logger.error(f"Failed to create crash input file: {crash.input_file}")
        return crash
    logger.debug(f"Crash input file created: {crash.input_file}")

    # Run the replay command using the specified command
    command = config["project"]["command"]
    replay_command = command.replace("@@", f"/tmp/{crash.input_file}")
    logger.debug(f"Replay command: {replay_command}")
    logger.debug(f"Environment: {env}")
    logger.debug(f"Working directory: {config['project']['directory']}")
    exit_code, output_str = engine.run_command(
        replay_command,
        workdir=config["project"]["directory"],
        env=env,
        timeout=REPLAY_TIMEOUT,
    )
    logger.debug(f"Replay output: {output_str.decode('utf-8', errors='replace')}")

    # Check the exit code to determine if the replay was successful
    if exit_code == 0:  # It should crash but it doesn't
        logger.debug("Replay failed. No crash detected.")
        type = CrashType.NON_REPRODUCIBLE
        return Crash(
            input_file=crash.input_file,
            input_content=crash.input_content,
            type=type,
            replay_result=replay_result,
        )
    elif exit_code == 124:  # Timeout
        logger.debug("Replay timed out.")
        type = CrashType.TIMEOUT
        return Crash(
            input_file=crash.input_file,
            input_content=crash.input_content,
            type=type,
            replay_result=replay_result,
        )

    # Check the log files in \tmp for ASAN and UBSAN reports
    files = engine.get_files("/out")
    for file_name, content in files.items():
        if file_name.startswith("asan"):
            replay_result += f"ASAN :\n {content}\n"
        if file_name.startswith("ubsan"):
            replay_result += f"UBSAN:\n {content}\n"

    # Check the log files for other errors
    if replay_result:
        logger.debug(f"Replay result: {replay_result}")
        type = CrashType.REPRODUCIBLE
        return Crash(
            input_file=crash.input_file,
            input_content=crash.input_content,
            type=type,
            replay_result=replay_result,
        )
    logger.debug("Replay failed. No crash detected.")
    type = CrashType.UNKNOWN
    return Crash(
        input_file=crash.input_file,
        input_content=crash.input_content,
        type=type,
        replay_result=replay_result,
    )
