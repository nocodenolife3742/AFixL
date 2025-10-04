import logging.config
import argparse

from afixl.config import LOG_DIR, LOG_CONFIG
from afixl.orchestration.manager import Manager

if __name__ == "__main__":

    # Set up logging configuration
    LOG_DIR.mkdir(exist_ok=True)
    logging.config.dictConfig(LOG_CONFIG)

    # Command-line argument parsing
    parser = argparse.ArgumentParser(
        description="A Conversational Large Language Model Agent for Automated Program Repair Guided by Fuzzing"
    )
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Path to the target configuration directory.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=360,
        help="Maximum allowed execution time for the system under test (in minutes).",
    )
    args = parser.parse_args()

    # Run the Manager with the provided path and timeout
    with Manager(args.path, args.timeout) as manager:
        manager.run()