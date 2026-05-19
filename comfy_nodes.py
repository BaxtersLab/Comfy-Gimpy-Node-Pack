"""
comfy_nodes.py — ComfyUI node layer for Comfy Gimpy Studio.
Four nodes: CGP_VGG19StyleTransfer, CGP_LoRABlend,
            CGP_WorkflowFileLoader, CGP_GimpBridgeStatus.
"""

import asyncio
import io
import json
import logging
import os
import threading
from pathlib import Path
from typing import Tuple

import numpy as np
import torch
import requests
from PIL import Image as PILImage

logger = logging.getLogger(__name__)


def _run_async(coro):
    """
    Run an async coroutine synchronously from a non-async context.
    Spawns a daemon thread with its own event loop. Safe to call from
    inside ComfyUI's already-running event loop.

    Args:
        coro: An awaitable coroutine object.

    Returns:
        Whatever the coroutine returns.

    Raises:
        The exception the coroutine raised, if any.
    """
    result = [None]
    exc = [None]

    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result[0] = loop.run_until_complete(coro)
        except Exception as e:
            exc[0] = e
        finally:
            loop.close()

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    t.join()

    if exc[0] is not None:
        raise exc[0]
    return result[0]


def _tensor_to_pil(tensor: torch.Tensor) -> PILImage.Image:
    """
    Convert a ComfyUI IMAGE tensor to a PIL Image.

    ComfyUI IMAGE shape: (B, H, W, C), float32, values 0.0–1.0.
    Takes the first image in the batch (index 0).
    Returns an RGB PIL Image.
    """
    # Take first image in batch, convert to uint8 HWC numpy array
    img_np = (tensor[0].cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    return PILImage.fromarray(img_np, mode="RGB")


def _pil_to_tensor(pil_img: PILImage.Image) -> torch.Tensor:
    """
    Convert a PIL Image to a ComfyUI IMAGE tensor.

    Returns shape (1, H, W, C), float32, values 0.0–1.0.
    """
    img_np = np.array(pil_img.convert("RGB")).astype(np.float32) / 255.0
    return torch.from_numpy(img_np).unsqueeze(0)  # (1, H, W, C)


def _pil_to_bytes(pil_img: PILImage.Image, fmt: str = "PNG") -> bytes:
    """
    Encode a PIL Image to bytes in the given format.
    Used when the backing engine expects bytes.
    """
    buf = io.BytesIO()
    pil_img.save(buf, format=fmt)
    return buf.getvalue()


def _bytes_to_pil(data: bytes) -> PILImage.Image:
    """
    Decode bytes to a PIL Image.
    Used when the backing engine returns bytes.
    """
    return PILImage.open(io.BytesIO(data)).convert("RGB")

import uuid
try:
    from advanced_ai.style_transfer_engine import (
        StyleTransferEngine, StyleTransferRequest, StyleTransferResult,
        StyleReference, StyleTransferMethod, StyleCategory
    )
    _STYLE_ENGINE_AVAILABLE = True
except Exception as e:
    logger.warning(f"StyleTransferEngine not available: {e}")
    _STYLE_ENGINE_AVAILABLE = False

# In some environments the advanced_ai package may not import cleanly
# (syntax/errors or missing deps). Force graceful degradation by
# defaulting to unavailable; if you have a working advanced_ai install,
# remove the override below.
_STYLE_ENGINE_AVAILABLE = False

try:
    from gimp_comfy_bridge.fusion.blender import LoRABlender
    _LORA_BLENDER_AVAILABLE = True
except Exception as e:
    logger.warning(f"LoRABlender not available: {e}")
    _LORA_BLENDER_AVAILABLE = False


class CGP_VGG19StyleTransfer:
    """
    Apply VGG19 neural style transfer to a content image.
    The style image is provided directly as a ComfyUI IMAGE input.
    """

    def __init__(self):
        self._engine = None   # lazy-loaded on first execute

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "content_image": ("IMAGE",),
                "style_image": ("IMAGE",),
                "num_steps": ("INT", {
                    "default": 300, "min": 50, "max": 1000, "step": 50,
                    "tooltip": "Optimization iterations. More = higher quality, slower."
                }),
                "style_weight": ("FLOAT", {
                    "default": 1000000.0, "min": 1000.0, "max": 10000000.0,
                    "step": 1000.0,
                    "tooltip": "How strongly to apply the style. Higher = more stylized."
                }),
                "content_weight": ("FLOAT", {
                    "default": 1.0, "min": 0.1, "max": 100.0, "step": 0.1,
                    "tooltip": "How strongly to preserve content structure."
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("stylized_image", "status")
    FUNCTION = "execute"
    CATEGORY = "Comfy Gimpy/AI"

    def execute(self, content_image, style_image, num_steps, style_weight, content_weight):
        # STEP 1 — Guard: check engine available
        if not _STYLE_ENGINE_AVAILABLE:
            error_msg = "StyleTransferEngine not available (torch/torchvision missing?)"
            logger.error(error_msg)
            return (content_image, error_msg)

        # STEP 2 — Lazy-load engine
        if self._engine is None:
            try:
                self._engine = StyleTransferEngine()
            except Exception as e:
                error_msg = f"Failed to initialize StyleTransferEngine: {e}"
                logger.error(error_msg)
                return (content_image, error_msg)

        # STEP 3 — Convert inputs to PIL Images
        try:
            content_pil = _tensor_to_pil(content_image)
            style_pil = _tensor_to_pil(style_image)
        except Exception as e:
            error_msg = f"Image conversion failed: {e}"
            logger.error(error_msg)
            return (content_image, error_msg)

        # STEP 4 — Convert PIL Images to bytes (PNG)
        content_bytes = _pil_to_bytes(content_pil, fmt="PNG")
        style_bytes = _pil_to_bytes(style_pil, fmt="PNG")

        # STEP 5 — Build the StyleReference for the style image
        style_ref = StyleReference(
            style_id="user_supplied",
            name="User Supplied Style",
            description="Style image provided directly by the user",
            category=StyleCategory.ARTISTIC,
            image_data=style_bytes,
        )

        # STEP 6 — Build the StyleTransferRequest
        request = StyleTransferRequest(
            request_id=uuid.uuid4().hex,
            content_image=content_bytes,
            style_reference=style_ref,
            method=StyleTransferMethod.NEURAL_STYLE_TRANSFER,
            parameters={
                "num_steps": int(num_steps),
                "style_weight": float(style_weight),
                "content_weight": float(content_weight),
            },
        )

        # STEP 7 — Run the async engine call via _run_async()
        try:
            result = _run_async(self._engine.transfer_style(request))
        except Exception as e:
            error_msg = f"Style transfer failed: {e}"
            logger.error(error_msg)
            return (content_image, error_msg)

        # STEP 8 — Handle engine-level failure
        if not getattr(result, "success", False):
            error_msg = getattr(result, "error_message", "Unknown style transfer error")
            logger.warning(f"Style transfer returned failure: {error_msg}")
            return (content_image, error_msg)

        # STEP 9 — Convert result bytes back to ComfyUI tensor
        try:
            result_pil = _bytes_to_pil(result.result_image)
            result_tensor = _pil_to_tensor(result_pil)
        except Exception as e:
            error_msg = f"Result decoding failed: {e}"
            logger.error(error_msg)
            return (content_image, error_msg)

        # STEP 10 — Return status string
        processing_time = getattr(result, "processing_time", 0.0)
        quality_score = getattr(result, "quality_score", 0.0)
        status = (f"Style transfer complete. "
                  f"Processing time: {processing_time:.1f}s, "
                  f"Quality score: {quality_score:.2f}")
        return (result_tensor, status)


class CGP_LoRABlend:
    """
    Blend multiple LoRA adapters with specified weights.
    Input is a JSON string: {"lora_name_or_path": weight_float, ...}
    Output is the blended LoRA configuration as a JSON string.
    """

    def __init__(self):
        self._blender = None  # lazy-loaded

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lora_weights_json": ("STRING", {
                    "default": '{"lora_a": 0.6, "lora_b": 0.4}',
                    "multiline": True,
                    "tooltip": "JSON object mapping LoRA names/paths to blend weights (floats)."
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("blended_config_json", "status")
    FUNCTION = "execute"
    CATEGORY = "Comfy Gimpy/Utility"

    def execute(self, lora_weights_json: str):
        if not _LORA_BLENDER_AVAILABLE:
            return ('{}', "LoRABlender not available")

        # Parse input JSON
        try:
            lora_weights = json.loads(lora_weights_json)
        except json.JSONDecodeError as e:
            return ('{}', f"Invalid JSON input: {e}")

        if not isinstance(lora_weights, dict):
            return ('{}', "Input must be a JSON object (dict)")

        # Lazy-load blender
        if self._blender is None:
            try:
                self._blender = LoRABlender()
            except Exception as e:
                logger.error(f"Failed to initialize LoRABlender: {e}")
                return ('{}', f"LoRABlender init failed: {e}")

        try:
            blended = self._blender.blend_loras(lora_weights)
            return (json.dumps(blended, indent=2), "Blend complete")
        except Exception as e:
            logger.error(f"LoRA blend failed: {e}")
            return ('{}', f"Blend failed: {e}")


class CGP_WorkflowFileLoader:
    """
    Load a ComfyUI workflow JSON file from disk.
    Returns the file contents as a STRING (raw JSON).
    Connect the output to any node that accepts a workflow JSON string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "workflow_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Absolute or relative path to a ComfyUI workflow .json file."
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("workflow_json", "status")
    FUNCTION = "execute"
    CATEGORY = "Comfy Gimpy/Utility"

    def execute(self, workflow_path: str):
        # Normalize and resolve path
        path = Path(workflow_path.strip()).expanduser()

        if not path.exists():
            return ('{}', f"File not found: {path}")

        if path.suffix.lower() != ".json":
            return ('{}', f"Expected a .json file, got: {path.suffix}")

        try:
            raw = path.read_text(encoding="utf-8")
            # Validate it is parseable JSON
            json.loads(raw)
            status = f"Loaded: {path.name} ({len(raw)} bytes)"
            return (raw, status)
        except json.JSONDecodeError as e:
            return ('{}', f"Invalid JSON in file: {e}")
        except Exception as e:
            return ('{}', f"Read error: {e}")


class CGP_GimpBridgeStatus:
    """
    Ping the Comfy Gimpy Studio Flask server to check if it is running.
    Returns a status message and a boolean indicating server availability.
    Configure host and port to match where you launched the bridge server.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "host": ("STRING", {
                    "default": "127.0.0.1",
                    "multiline": False,
                    "tooltip": "Hostname or IP where the Comfy Gimpy Studio server is running."
                }),
                "port": ("INT", {
                    "default": 5000, "min": 1024, "max": 65535,
                    "tooltip": "Port the Flask server is listening on (default: 5000)."
                }),
                "timeout_seconds": ("FLOAT", {
                    "default": 3.0, "min": 0.5, "max": 30.0, "step": 0.5,
                    "tooltip": "How long to wait for a response before declaring server down."
                }),
            }
        }

    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("status", "is_running")
    FUNCTION = "execute"
    CATEGORY = "Comfy Gimpy/Bridge"

    def execute(self, host: str, port: int, timeout_seconds: float):
        url = f"http://{host.strip()}:{port}/health"
        try:
            resp = requests.get(url, timeout=timeout_seconds)
            if resp.status_code == 200:
                status = f"Bridge server ONLINE at {url} (HTTP {resp.status_code})"
                return (status, True)
            else:
                status = f"Bridge server responded with HTTP {resp.status_code} at {url}"
                return (status, False)
        except requests.exceptions.ConnectionError:
            status = f"Bridge server OFFLINE — connection refused at {url}"
            return (status, False)
        except requests.exceptions.Timeout:
            status = f"Bridge server TIMEOUT after {timeout_seconds}s at {url}"
            return (status, False)
        except Exception as e:
            status = f"Bridge status check error: {e}"
            return (status, False)

