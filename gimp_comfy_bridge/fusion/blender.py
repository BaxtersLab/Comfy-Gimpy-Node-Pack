"""
LoRA blending and style mixing utilities.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json
import hashlib

logger = logging.getLogger(__name__)


class LoRABlender:
    """Handles LoRA weight blending operations."""

    def __init__(self):
        self.cache_dir = Path("cache/lora_blends")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def blend_loras(self, lora_weights: Dict[str, float]) -> Dict[str, Any]:
        """
        Blend multiple LoRAs with specified weights.

        Args:
            lora_weights: Dict mapping LoRA paths/IDs to weights

        Returns:
            Blended LoRA configuration
        """
        if not lora_weights:
            return {}

        # Create cache key from weights
        weights_str = json.dumps(lora_weights, sort_keys=True)
        cache_key = hashlib.md5(weights_str.encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"

        # Check cache first
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_result = json.load(f)
                logger.info(f"Loaded blended LoRA from cache: {cache_key}")
                return cached_result
            except Exception as e:
                logger.warning(f"Failed to load cached blend: {e}")

        # Perform blending
        blended_config = self._perform_blending(lora_weights)

        # Cache result
        try:
            with open(cache_file, 'w') as f:
                json.dump(blended_config, f, indent=2)
            logger.info(f"Cached blended LoRA: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache blend: {e}")

        return blended_config

    def _perform_blending(self, lora_weights: Dict[str, float]) -> Dict[str, Any]:
        """Perform the actual LoRA blending logic."""
        # Normalize weights
        total_weight = sum(lora_weights.values())
        if total_weight == 0:
            return {}

        normalized_weights = {
            lora: weight / total_weight
            for lora, weight in lora_weights.items()
        }

        # Create blended configuration
        blended_config = {
            "type": "blended_lora",
            "loras": list(lora_weights.keys()),
            "weights": list(normalized_weights.values()),
            "normalized_weights": normalized_weights,
            "total_weight": total_weight,
            "blend_hash": hashlib.md5(
                json.dumps(normalized_weights, sort_keys=True).encode()
            ).hexdigest()[:8]
        }

        logger.info(f"Blended {len(lora_weights)} LoRAs with total weight {total_weight}")
        return blended_config

    def get_blend_info(self, blend_hash: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific blend."""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    if data.get("blend_hash") == blend_hash:
                        return data
            except Exception:
                continue
        return None


class StyleMixer:
    """Handles multi-style mixing operations."""

    def __init__(self):
        self.cache_dir = Path("cache/style_mixes")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def mix_styles(self,
                   styles: List[Dict[str, Any]],
                   ratios: List[float]) -> Dict[str, Any]:
        """
        Mix multiple styles with specified ratios.

        Args:
            styles: List of style definitions
            ratios: Mixing ratios (should sum to 1.0)

        Returns:
            Mixed style configuration
        """
        if len(styles) != len(ratios):
            raise ValueError("Number of styles must match number of ratios")

        if not styles:
            return {}

        # Normalize ratios
        total_ratio = sum(ratios)
        if total_ratio == 0:
            return styles[0]  # Return first style if all ratios are 0

        normalized_ratios = [r / total_ratio for r in ratios]

        # Create cache key
        style_ids = [s.get('id', str(i)) for i, s in enumerate(styles)]
        mix_key = f"{'_'.join(style_ids)}_{'_'.join(f'{r:.3f}' for r in normalized_ratios)}"
        cache_key = hashlib.md5(mix_key.encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"

        # Check cache
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_result = json.load(f)
                logger.info(f"Loaded mixed style from cache: {cache_key}")
                return cached_result
            except Exception as e:
                logger.warning(f"Failed to load cached mix: {e}")

        # Perform mixing
        mixed_style = self._perform_mixing(styles, normalized_ratios)

        # Cache result
        try:
            with open(cache_file, 'w') as f:
                json.dump(mixed_style, f, indent=2)
            logger.info(f"Cached mixed style: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache mix: {e}")

        return mixed_style

    def _perform_mixing(self,
                       styles: List[Dict[str, Any]],
                       ratios: List[float]) -> Dict[str, Any]:
        """Perform the actual style mixing logic."""
        if len(styles) == 1:
            return styles[0]

        # Create mixed style
        mixed_style = {
            "id": f"mixed_{'_'.join(s.get('id', str(i)) for i, s in enumerate(styles))}",
            "name": f"Mixed: {', '.join(s.get('name', f'Style {i+1}') for i, s in enumerate(styles))}",
            "type": "mixed_style",
            "source_styles": [s.get('id', str(i)) for i, s in enumerate(styles)],
            "mix_ratios": ratios,
            "components": {}
        }

        # Mix style components (prompts, LoRAs, etc.)
        for component_type in ["positive_prompt", "negative_prompt", "loras", "embeddings"]:
            component_values = []
            for style, ratio in zip(styles, ratios):
                if component_type in style:
                    component_values.append((style[component_type], ratio))

            if component_values:
                mixed_component = self._mix_component(component_values, component_type)
                if mixed_component:
                    mixed_style["components"][component_type] = mixed_component

        logger.info(f"Mixed {len(styles)} styles with ratios {ratios}")
        return mixed_style

    def _mix_component(self,
                      component_values: List[tuple],
                      component_type: str) -> Any:
        """Mix a specific component type."""
        if component_type in ["positive_prompt", "negative_prompt"]:
            # Concatenate prompts with weights
            mixed_parts = []
            for prompt, ratio in component_values:
                if isinstance(prompt, str) and ratio > 0.1:  # Only include significant ratios
                    weight_str = f"({prompt}:{ratio:.2f})" if ratio != 1.0 else prompt
                    mixed_parts.append(weight_str)
            return ", ".join(mixed_parts)

        elif component_type == "loras":
            # Merge LoRA dictionaries
            merged_loras = {}
            for lora_dict, ratio in component_values:
                if isinstance(lora_dict, dict):
                    for lora_name, lora_config in lora_dict.items():
                        if lora_name not in merged_loras:
                            merged_loras[lora_name] = lora_config.copy()
                        # Weight the LoRA strength
                        if "strength" in merged_loras[lora_name]:
                            merged_loras[lora_name]["strength"] = (
                                merged_loras[lora_name]["strength"] * (1 - ratio) +
                                lora_config.get("strength", 1.0) * ratio
                            )
            return merged_loras

        elif component_type == "embeddings":
            # Merge embedding lists
            merged_embeddings = []
            for embedding_list, ratio in component_values:
                if isinstance(embedding_list, list):
                    for embedding in embedding_list:
                        if embedding not in merged_embeddings:
                            merged_embeddings.append(embedding)
            return merged_embeddings

        return None