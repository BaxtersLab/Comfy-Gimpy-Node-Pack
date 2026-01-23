"""
Remote ComfyUI Node Capabilities Detection.

Detects and reports capabilities of remote ComfyUI nodes including VRAM,
installed models, LoRAs, and supported workflows.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
import aiohttp

from ..shared.types import NodeCapabilities, ModelInfo, LoRAInfo, WorkflowSupport

logger = logging.getLogger(__name__)


async def detect_capabilities(node_url: str, token: str) -> NodeCapabilities:
    """
    Detect capabilities of a remote ComfyUI node.

    Args:
        node_url: Node URL
        token: Authentication token

    Returns:
        Node capabilities

    Raises:
        Exception: If capability detection fails
    """
    async with aiohttp.ClientSession(
        headers={'Authorization': f'Bearer {token}'},
        timeout=aiohttp.ClientTimeout(total=30)
    ) as session:

        try:
            # Get system stats for hardware info
            system_stats = await _get_system_stats(session, node_url)

            # Get installed models
            models = await _get_installed_models(session, node_url)

            # Get installed LoRAs
            loras = await _get_installed_loras(session, node_url)

            # Get supported workflows
            workflows = await _get_supported_workflows(session, node_url)

            # Calculate capabilities
            capabilities = NodeCapabilities(
                vram_gb=system_stats.get('vram_gb', 0),
                gpu_name=system_stats.get('gpu_name', 'Unknown'),
                cpu_cores=system_stats.get('cpu_cores', 0),
                ram_gb=system_stats.get('ram_gb', 0),
                installed_models=models,
                installed_loras=loras,
                supported_workflows=workflows,
                cuda_version=system_stats.get('cuda_version'),
                pytorch_version=system_stats.get('pytorch_version'),
                comfyui_version=system_stats.get('comfyui_version'),
                detected_at=asyncio.get_event_loop().time()
            )

            logger.info(f"Detected capabilities for node {node_url}: "
                       f"VRAM={capabilities.vram_gb}GB, "
                       f"Models={len(capabilities.installed_models)}, "
                       f"LoRAs={len(capabilities.installed_loras)}")

            return capabilities

        except Exception as e:
            logger.error(f"Failed to detect capabilities for node {node_url}: {e}")
            raise


async def _get_system_stats(session: aiohttp.ClientSession, node_url: str) -> Dict[str, Any]:
    """
    Get system statistics from the node.

    Args:
        session: HTTP session
        node_url: Node URL

    Returns:
        System statistics
    """
    try:
        async with session.get(f"{node_url}/system_stats") as response:
            if response.status != 200:
                logger.warning(f"Failed to get system stats: HTTP {response.status}")
                return {}

            data = await response.json()
            return data.get('system', {})

    except Exception as e:
        logger.warning(f"Error getting system stats: {e}")
        return {}


async def _get_installed_models(session: aiohttp.ClientSession, node_url: str) -> List[ModelInfo]:
    """
    Get list of installed models from the node.

    Args:
        session: HTTP session
        node_url: Node URL

    Returns:
        List of installed models
    """
    try:
        async with session.get(f"{node_url}/models") as response:
            if response.status != 200:
                logger.warning(f"Failed to get models: HTTP {response.status}")
                return []

            data = await response.json()
            models_data = data.get('models', [])

            models = []
            for model_data in models_data:
                try:
                    model = ModelInfo(
                        name=model_data.get('name', 'Unknown'),
                        type=model_data.get('type', 'unknown'),
                        size_gb=model_data.get('size_gb', 0),
                        format=model_data.get('format', 'unknown'),
                        path=model_data.get('path', ''),
                        metadata=model_data.get('metadata', {})
                    )
                    models.append(model)
                except Exception as e:
                    logger.warning(f"Error parsing model data: {e}")

            return models

    except Exception as e:
        logger.warning(f"Error getting installed models: {e}")
        return []


async def _get_installed_loras(session: aiohttp.ClientSession, node_url: str) -> List[LoRAInfo]:
    """
    Get list of installed LoRAs from the node.

    Args:
        session: HTTP session
        node_url: Node URL

    Returns:
        List of installed LoRAs
    """
    try:
        async with session.get(f"{node_url}/loras") as response:
            if response.status != 200:
                logger.warning(f"Failed to get LoRAs: HTTP {response.status}")
                return []

            data = await response.json()
            loras_data = data.get('loras', [])

            loras = []
            for lora_data in loras_data:
                try:
                    lora = LoRAInfo(
                        name=lora_data.get('name', 'Unknown'),
                        trigger_words=lora_data.get('trigger_words', []),
                        strength_min=lora_data.get('strength_min', 0.0),
                        strength_max=lora_data.get('strength_max', 1.0),
                        path=lora_data.get('path', ''),
                        metadata=lora_data.get('metadata', {})
                    )
                    loras.append(lora)
                except Exception as e:
                    logger.warning(f"Error parsing LoRA data: {e}")

            return loras

    except Exception as e:
        logger.warning(f"Error getting installed LoRAs: {e}")
        return []


async def _get_supported_workflows(session: aiohttp.ClientSession, node_url: str) -> List[WorkflowSupport]:
    """
    Get list of supported workflows from the node.

    Args:
        session: HTTP session
        node_url: Node URL

    Returns:
        List of supported workflows
    """
    try:
        async with session.get(f"{node_url}/workflows") as response:
            if response.status != 200:
                logger.warning(f"Failed to get workflows: HTTP {response.status}")
                return []

            data = await response.json()
            workflows_data = data.get('workflows', [])

            workflows = []
            for workflow_data in workflows_data:
                try:
                    workflow = WorkflowSupport(
                        name=workflow_data.get('name', 'Unknown'),
                        category=workflow_data.get('category', 'general'),
                        inputs=workflow_data.get('inputs', []),
                        outputs=workflow_data.get('outputs', []),
                        required_models=workflow_data.get('required_models', []),
                        estimated_time=workflow_data.get('estimated_time', 0),
                        metadata=workflow_data.get('metadata', {})
                    )
                    workflows.append(workflow)
                except Exception as e:
                    logger.warning(f"Error parsing workflow data: {e}")

            return workflows

    except Exception as e:
        logger.warning(f"Error getting supported workflows: {e}")
        return []


async def validate_node_compatibility(node_url: str,
                                    token: str,
                                    required_capabilities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Validate if a node meets required capabilities.

    Args:
        node_url: Node URL
        token: Authentication token
        required_capabilities: Required capabilities to check

    Returns:
        Validation results with compatibility score and missing features
    """
    if not required_capabilities:
        return {
            'compatible': True,
            'score': 1.0,
            'missing_features': [],
            'warnings': []
        }

    try:
        capabilities = await detect_capabilities(node_url, token)

        missing_features = []
        warnings = []
        score = 1.0

        # Check VRAM requirements
        required_vram = required_capabilities.get('min_vram_gb')
        if required_vram and capabilities.vram_gb < required_vram:
            missing_features.append(f"Insufficient VRAM: {capabilities.vram_gb}GB < {required_vram}GB required")
            score *= 0.5

        # Check required models
        required_models = required_capabilities.get('required_models', [])
        installed_model_names = {model.name for model in capabilities.installed_models}

        for req_model in required_models:
            if req_model not in installed_model_names:
                missing_features.append(f"Missing required model: {req_model}")
                score *= 0.7

        # Check workflow support
        required_workflow = required_capabilities.get('required_workflow')
        if required_workflow:
            workflow_names = {wf.name for wf in capabilities.supported_workflows}
            if required_workflow not in workflow_names:
                missing_features.append(f"Missing required workflow: {required_workflow}")
                score *= 0.8

        # Check CUDA version compatibility
        required_cuda = required_capabilities.get('min_cuda_version')
        if required_cuda and capabilities.cuda_version:
            # Simple version comparison (could be more sophisticated)
            if capabilities.cuda_version < required_cuda:
                warnings.append(f"CUDA version {capabilities.cuda_version} may be outdated "
                              f"(required: {required_cuda})")

        compatible = len(missing_features) == 0

        return {
            'compatible': compatible,
            'score': score,
            'missing_features': missing_features,
            'warnings': warnings,
            'capabilities': capabilities
        }

    except Exception as e:
        logger.error(f"Failed to validate node compatibility: {e}")
        return {
            'compatible': False,
            'score': 0.0,
            'missing_features': [f"Validation failed: {e}"],
            'warnings': [],
            'capabilities': None
        }