from typing import Literal
from pydantic import BaseModel

# Define types for supported standards, sanitizers, crash stages, and patches
CrashStage = Literal["fuzz", "replay", "repair", "evaluate"]


# Define the crash model
class RequestCode(BaseModel):
    reason: str  # Reason for requesting the code
    line: int  # Line number in the file
    file: str  # File path of source code to be requested


class ModifiedLine(BaseModel):
    line_number: int  # Line number in the file
    content: list[str]  # List of strings representing the modified lines


class Patch(BaseModel):
    file: str  # File path where the patch should be applied
    diff: list[ModifiedLine]  # List of line changes


class ProposedPatch(BaseModel):
    reason: str  # Reason for proposing the patch
    patches: list[Patch]  # List of patches to apply


class MakeNote(BaseModel):
    content: str  # Note content


class Crash(BaseModel, ser_json_bytes="base64"):
    id: str
    stage: CrashStage
    repo_addr: str
    fix_commit: str
    project: str
    report: bytes | None = None
    requested_content: dict[str, dict[int, str]] = {}  # Requested source code content
    note: list[str] = []  # Notes about the crash
    valid_patches: list[Patch] | None = None  # Valid patch if available
    retry_count: int = 0  # Number of repair attempts
    history: list[RequestCode | ProposedPatch | MakeNote] = (
        []
    )  # History of actions taken on the crash
