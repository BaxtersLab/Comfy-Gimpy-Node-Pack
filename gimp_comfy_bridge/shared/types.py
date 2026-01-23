"""
Type definitions for the bridge.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class HistoryMetadata:
    """
    Metadata for a history step.
    """
    step: int
    timestamp: str
    workflow: str
    mode: str
    input_file: Optional[str]
    mask_file: Optional[str]
    output_file: str
    params_file: str
    notes: str

@dataclass
class WorkflowParams:
    """
    Parameters for workflow execution.
    """
    prompt: Optional[str]
    negative_prompt: Optional[str]
    width: Optional[int]
    height: Optional[int]
    strength: Optional[float]
    upscale_factor: Optional[float]
    model: Optional[str]
    loras: Optional[list]
    controlnet: Optional[list]