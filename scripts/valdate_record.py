import json

# read all the files in the folder "records"
import os
import glob
import sys
import argparse

# 42471500 42470538 42471526

def validate_record(record: dict) -> bool:
    return len(record["history"]) == 15


def main(folder_path: str):
    json_files = glob.glob(os.path.join(folder_path, "*.json"))
    if not json_files:
        print(f"No JSON files found in folder: {folder_path}")
        return

    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                record = json.load(f)
                if not validate_record(record):
                    print(f"Validation failed for file: {json_file}")

            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from file {json_file}: {e}")


if __name__ == "__main__":
    main("records")
