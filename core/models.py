from typing import Literal, Any
from pathlib import Path
from pydantic import BaseModel, Field

RadiusCommand = Literal["auth", "reauth", "start", "alive", "stop"]
Vendor = Literal["mikrotik", "cisco", "fortigate"]

class Step(BaseModel):
    command: RadiusCommand
    delay_before: int = Field(0, ge=0, description="Milliseconds to wait before executing this step")
    avps: dict[str, Any] = Field({}, description="Custom Attribute-Value Pairs for this step")

class ConnectionConfig(BaseModel):
    server: str
    secret: str
    vendor: Vendor
    username: str
    password: str

class Session(BaseModel):
    name: str
    config: ConnectionConfig
    sequence: list[Step]


class ExecutionPlan(BaseModel):
    """Defines a multi-session execution plan."""
    name: str
    mode: Literal["sequential", "parallel", "async"] = "sequential"
    session_files: list[Path] = Field(..., description="List of paths to session YAML files to execute.")
