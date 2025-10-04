from typing import Literal, Annotated
from pydantic import BaseModel, Field
import uuid

# Define types for supported standards, sanitizers, crash stages, and patches
SupportedStandard = Literal[
    "c++98",
    "c++11",
    "c++14",
    "c++17",
    "c++20",
    "c++23",
    "c89",
    "c99",
    "c11",
    "c17",
    "c23",
]
CrashStage = Literal["fuzz", "replay", "repair", "evaluate"]


# Define the Config model
class Project(BaseModel):
    standard: SupportedStandard
    executable: str


class Environment(BaseModel):
    runtime: dict[str, str]
    build: dict[str, str]


class Config(BaseModel):
    project: Project
    environment: Environment
    path: str


# Define the crash model
class RequestCode(BaseModel):
    reason: str  # Reason for requesting the code
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
    confidence: float = 0.0  # Confidence score for the proposed patch


class MakeNote(BaseModel):
    content: str  # Note content


class Crash(BaseModel, ser_json_bytes='base64'):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stage: CrashStage
    reproducable: bool | None = None
    input: bytes
    report: bytes | None = None
    requested_content: dict[str, bytes] = {}  # Requested source code content
    note: list[str] = []  # Notes about the crash
    valid_patches: list[Patch] | None = None  # Valid patch if available
    retry_count: int = 0  # Number of repair attempts
    history: list[RequestCode | ProposedPatch | MakeNote] = (
        []
    )  # History of actions taken on the crash
