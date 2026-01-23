"""
Model registry for Comfy Gimpy Studio.
Manages local model discovery and registration.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from .config import load_config

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Registry for managing local models.
    """

    def __init__(self):
        self.config = None
        self.models = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Ensure models are loaded."""
        if not self._loaded:
            self.config = load_config()
            self._scan_models()
            self._loaded = True

    def _scan_models(self):
        """Scan for available models."""
        # This is a stub implementation
        # In a real implementation, this would scan model directories
        # and read metadata files

        self.models = {
            "checkpoints": [
                {
                    "name": "SDXL 1.0",
                    "path": "models/checkpoints/sdxl_1.0.safetensors",
                    "type": "checkpoint",
                    "description": "Stable Diffusion XL 1.0 base model"
                }
            ],
            "loras": [],
            "controlnets": [],
            "embeddings": []
        }

    def scan_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scan and return all available models.

        Returns:
            Dict with model categories and their models
        """
        self._ensure_loaded()
        return self.models

    def register_model(self, model_info: Dict[str, Any]) -> bool:
        """
        Register a new model in the registry.

        Args:
            model_info (dict): Model information

        Returns:
            bool: True if successful
        """
        try:
            model_type = model_info.get("type", "checkpoint")
            if model_type not in self.models:
                self.models[model_type] = []

            self.models[model_type].append(model_info)
            logger.info(f"Registered model: {model_info.get('name')}")
            return True

        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            return False

    def get_model_metadata(self, model_path: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a model.

        Args:
            model_path (str): Model path

        Returns:
            Model metadata or None
        """
        self._ensure_loaded()

        for category, models in self.models.items():
            for model in models:
                if model.get("path") == model_path:
                    return model

        return None


# Global registry instance
_registry = ModelRegistry()


def scan_models() -> Dict[str, List[Dict[str, Any]]]:
    """
    Scan and return all available models.

    Returns:
        Dict with model categories and their models
    """
    return _registry.scan_models()


def register_model(model_info: Dict[str, Any]) -> bool:
    """
    Register a new model.

    Args:
        model_info (dict): Model information

    Returns:
        bool: True if successful
    """
    return _registry.register_model(model_info)


def get_model_metadata(model_path: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a model.

    Args:
        model_path (str): Model path

    Returns:
        Model metadata or None
    """
    return _registry.get_model_metadata(model_path)