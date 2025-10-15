import subprocess
import os
import json
import argparse
import base64


REPORT_TEMPLATE = """
## Patch ID
{patch_id}

## Crash Input
```
{crash_input}
```

## Crash Report
```
{crash_report}
```

## Fix Description
{fix_description}

## Notes
- Some characters in the crash input and report may not render properly due to encoding issues. Please refer to the raw files for accurate representation.
"""


def base64_decode(data):
    """Decode base64, padding being optional.

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    return base64.b64decode(data)


def patch_application(patches, repo_path):
    """
    Apply the proposed patches to the source code.
    This method should contain the logic for applying patches.
    """
    for patch in patches:
        processed_lines = set()
        file_path = patch["file"]
        if file_path.startswith("/"):
            file_path = file_path[1:]
        with open(os.path.join(repo_path, file_path), "r") as f:
            raw_content = f.read()
        lines = raw_content.splitlines(keepends=True)

        for modified_line in patch["diff"]:
            line_number = modified_line["line_number"] - 1
            if 0 <= line_number < len(lines) and line_number not in processed_lines:
                lines[line_number] = "\n".join(modified_line["content"]) + "\n"
                processed_lines.add(line_number)
            else:
                return False

        new_content = "".join(lines)
        with open(os.path.join(repo_path, file_path), "w") as f:
            f.write(new_content)

    return True


def create_patch_branch(file_path, repo_path, patches_dir, base_branch):
    branch_name = f"patch/{file_path.split('.')[0]}"
    print(f"Creating and switching to branch: {branch_name}")
    subprocess.run(["git", "-C", repo_path, "checkout", "-b", branch_name])

    # read the JSON file
    with open(os.path.join(patches_dir, file_path), "r") as f:
        data = json.load(f)
    patch_application(data["valid_patches"], repo_path)

    subprocess.run(["git", "-C", repo_path, "add", "."])
    subprocess.run(
        [
            "git",
            "-C",
            repo_path,
            "commit",
            "-m",
            f"Applied patch id {file_path.split('.')[0]}",
        ]
    )
    subprocess.run(["git", "-C", repo_path, "push", "-u", "origin", branch_name])

    # create a markdown report in the temporary directory
    report_content = REPORT_TEMPLATE.format(
        patch_id=file_path.split(".")[0],
        crash_input=base64_decode(data["input"]).decode("utf-8", errors="replace"),
        crash_report=base64_decode(data["report"]).decode("utf-8", errors="replace"),
        fix_description=data["history"][-1]["reason"],
    )
    
    with open(os.path.join(repo_path, "PATCH_REPORT.md"), "w") as f:
        f.write(report_content)

    # # pull request creation can be automated using GitHub CLI
    subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base_branch,
            "--head",
            branch_name,
            "--title",
            f"\"Patch {file_path.split('.')[0]}\"",
            "--body-file",
            os.path.join(repo_path, "PATCH_REPORT.md"),
        ],
        check=True,
        cwd=repo_path,
    )
    print(f"Pull request created for branch: {branch_name}")


def main():
    parser = argparse.ArgumentParser(
        description="Process patch JSON files and create git branches."
    )
    parser.add_argument(
        "--patches-dir",
        type=str,
        help="Directory containing patch JSON files (required)",
        required=True,
    )
    parser.add_argument(
        "--repo-dir",
        type=str,
        help="Directory containing the git repository (required)",
        required=True,
    )
    args = parser.parse_args()

    current_branch = (
        subprocess.check_output(
            ["git", "-C", args.repo_dir, "rev-parse", "--abbrev-ref", "HEAD"]
        )
        .strip()
        .decode("utf-8")
    )

    print(f"Current Git branch: {current_branch}")

    for file in os.listdir(args.patches_dir):
        if file.endswith(".json"):
            print(f"Processing file: {file}")
            subprocess.run(["git", "-C", args.repo_dir, "checkout", current_branch])
            create_patch_branch(file, args.repo_dir, args.patches_dir, current_branch)


if __name__ == "__main__":
    main()
