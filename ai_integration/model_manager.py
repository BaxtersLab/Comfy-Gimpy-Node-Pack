"""
Model Manager
Handles AI model loading, management, and optimization for the Creative Director
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import torch
import json

class ModelManager:
    """
    Manages AI models for creative direction and analysis
    """

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Model registry
        self.models = {}
        self.model_configs = {}
        self.loaded_models = {}

        # Performance tracking
        self.model_performance = {}
        self.memory_usage = {}

        # Initialize model registry
        self._initialize_model_registry()

    def _initialize_model_registry(self):
        """Initialize the model registry with available models"""
        self.model_configs = {
            "clip-vit-base-patch32": {
                "type": "vision",
                "purpose": "image_analysis",
                "memory_mb": 512,
                "gpu_required": False,
                "description": "CLIP model for image-text similarity"
            },
            "microsoft/DialoGPT-medium": {
                "type": "language",
                "purpose": "conversation",
                "memory_mb": 1024,
                "gpu_required": False,
                "description": "Conversational AI for creative guidance"
            },
            "openai/clip-vit-large-patch14": {
                "type": "vision",
                "purpose": "style_analysis",
                "memory_mb": 2048,
                "gpu_required": True,
                "description": "Advanced CLIP model for detailed style analysis"
            },
            "stabilityai/stable-diffusion-2-1": {
                "type": "generation",
                "purpose": "image_generation",
                "memory_mb": 4096,
                "gpu_required": True,
                "description": "Stable Diffusion for creative image generation"
            },
            "facebook/opt-1.3b": {
                "type": "language",
                "purpose": "text_generation",
                "memory_mb": 2048,
                "gpu_required": True,
                "description": "OPT model for creative text generation"
            }
        }

    def load_model(self, model_name: str, device: str = "auto") -> bool:
        """
        Load a model into memory

        Args:
            model_name: Name of the model to load
            device: Device to load on ('cpu', 'cuda', 'auto')

        Returns:
            Success status
        """
        try:
            if model_name not in self.model_configs:
                self.logger.error(f"Unknown model: {model_name}")
                return False

            if model_name in self.loaded_models:
                self.logger.info(f"Model {model_name} already loaded")
                return True

            config = self.model_configs[model_name]

            # Determine device
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() and config.get("gpu_required", False) else "cpu"

            # Check memory requirements
            if not self._check_memory_requirements(config, device):
                self.logger.error(f"Insufficient memory for model {model_name}")
                return False

            # Load model (simplified - in real implementation would load actual models)
            self.logger.info(f"Loading model {model_name} on {device}")

            # Mock model loading
            model_instance = self._create_mock_model(model_name, config)

            self.loaded_models[model_name] = {
                "instance": model_instance,
                "device": device,
                "loaded_at": datetime.now(),
                "config": config
            }

            # Track memory usage
            self.memory_usage[model_name] = config["memory_mb"]

            self.logger.info(f"Successfully loaded model {model_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {e}")
            return False

    def _create_mock_model(self, model_name: str, config: Dict[str, Any]) -> Any:
        """Create a mock model instance for development"""
        class MockModel:
            def __init__(self, name, config):
                self.name = name
                self.config = config

            def __call__(self, *args, **kwargs):
                return {"result": f"Mock output from {self.name}"}

        return MockModel(model_name, config)

    def _check_memory_requirements(self, config: Dict[str, Any], device: str) -> bool:
        """Check if system has sufficient memory for the model"""
        required_mb = config.get("memory_mb", 0)

        if device == "cuda":
            if not torch.cuda.is_available():
                return False
            # Check GPU memory (simplified)
            return True  # Assume sufficient GPU memory
        else:
            # Check system memory (simplified)
            return True  # Assume sufficient system memory

    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model from memory

        Args:
            model_name: Name of the model to unload

        Returns:
            Success status
        """
        try:
            if model_name not in self.loaded_models:
                return False

            # Unload model
            del self.loaded_models[model_name]

            # Free memory tracking
            if model_name in self.memory_usage:
                del self.memory_usage[model_name]

            self.logger.info(f"Unloaded model {model_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to unload model {model_name}: {e}")
            return False

    def get_model(self, model_name: str) -> Optional[Any]:
        """Get a loaded model instance"""
        if model_name not in self.loaded_models:
            return None
        return self.loaded_models[model_name]["instance"]

    def is_model_loaded(self, model_name: str) -> bool:
        """Check if a model is loaded"""
        return model_name in self.loaded_models

    def get_loaded_models(self) -> List[str]:
        """Get list of currently loaded models"""
        return list(self.loaded_models.keys())

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a model"""
        if model_name not in self.model_configs:
            return None

        info = self.model_configs[model_name].copy()

        if model_name in self.loaded_models:
            info["loaded"] = True
            info["device"] = self.loaded_models[model_name]["device"]
            info["loaded_at"] = self.loaded_models[model_name]["loaded_at"]
        else:
            info["loaded"] = False

        return info

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """
        Optimize memory usage by unloading unused models

        Returns:
            Optimization results
        """
        results = {
            "freed_memory_mb": 0,
            "unloaded_models": [],
            "optimization_timestamp": datetime.now()
        }

        # Simple optimization: unload models not used recently
        current_time = datetime.now()

        to_unload = []
        for model_name, model_data in self.loaded_models.items():
            # If loaded more than 30 minutes ago, consider unloading
            if (current_time - model_data["loaded_at"]).seconds > 1800:
                to_unload.append(model_name)

        for model_name in to_unload:
            if self.unload_model(model_name):
                results["freed_memory_mb"] += self.memory_usage.get(model_name, 0)
                results["unloaded_models"].append(model_name)

        return results

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics"""
        total_memory = sum(self.memory_usage.values())

        return {
            "total_memory_mb": total_memory,
            "models_loaded": len(self.loaded_models),
            "memory_by_model": self.memory_usage.copy(),
            "available_models": list(self.model_configs.keys())
        }

    def update_model_performance(self, model_name: str, performance_data: Dict[str, Any]):
        """
        Update performance metrics for a model

        Args:
            model_name: Name of the model
            performance_data: Performance metrics
        """
        if model_name not in self.model_performance:
            self.model_performance[model_name] = []

        performance_data["timestamp"] = datetime.now()
        self.model_performance[model_name].append(performance_data)

        # Keep only recent performance data (last 100 entries)
        if len(self.model_performance[model_name]) > 100:
            self.model_performance[model_name] = self.model_performance[model_name][-100:]

    def get_model_performance(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get performance statistics for a model"""
        if model_name not in self.model_performance:
            return None

        performances = self.model_performance[model_name]
        if not performances:
            return None

        # Calculate statistics
        response_times = [p.get("response_time", 0) for p in performances]
        accuracies = [p.get("accuracy", 0) for p in performances]

        return {
            "model_name": model_name,
            "total_runs": len(performances),
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "avg_accuracy": sum(accuracies) / len(accuracies) if accuracies else 0,
            "last_updated": performances[-1]["timestamp"] if performances else None
        }

    def save_model_registry(self, filepath: str) -> bool:
        """Save model registry to file"""
        try:
            data = {
                "model_configs": self.model_configs,
                "model_performance": self.model_performance,
                "export_timestamp": datetime.now().isoformat()
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            return True

        except Exception as e:
            self.logger.error(f"Failed to save model registry: {e}")
            return False

    def load_model_registry(self, filepath: str) -> bool:
        """Load model registry from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.model_configs = data.get("model_configs", {})
            self.model_performance = data.get("model_performance", {})

            return True

        except Exception as e:
            self.logger.error(f"Failed to load model registry: {e}")
            return False