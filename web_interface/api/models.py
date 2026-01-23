"""
Models API for web interface.
Handles model browsing, downloading, and management.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from aiohttp import ClientSession
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


class ModelBrowser:
    """
    Model browser for downloading models from Civitai and HuggingFace.
    """

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        if AIOHTTP_AVAILABLE:
            self.session = ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def search_civitai(self, query: str, model_type: str = "Checkpoint", limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search models on Civitai.

        Args:
            query (str): Search query
            model_type (str): Model type (Checkpoint, LoRA, etc.)
            limit (int): Maximum results

        Returns:
            List of model dictionaries
        """
        if not self.session:
            return []

        try:
            # Civitai API search
            url = "https://civitai.com/api/v1/models"
            params = {
                "query": query,
                "types": model_type,
                "limit": limit
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_civitai_results(data.get("items", []))
                else:
                    logger.error(f"Civitai API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Failed to search Civitai: {e}")
            return []

    async def search_huggingface(self, query: str, model_type: str = "checkpoint", limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search models on HuggingFace.

        Args:
            query (str): Search query
            model_type (str): Model type
            limit (int): Maximum results

        Returns:
            List of model dictionaries
        """
        if not self.session:
            return []

        try:
            # HuggingFace API search
            url = "https://huggingface.co/api/models"
            params = {
                "search": query,
                "limit": limit,
                "filter": model_type
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_huggingface_results(data)
                else:
                    logger.error(f"HuggingFace API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Failed to search HuggingFace: {e}")
            return []

    def _parse_civitai_results(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse Civitai API results."""
        results = []
        for item in items:
            # Get the first model version
            version = item.get("modelVersions", [{}])[0] if item.get("modelVersions") else {}

            result = {
                "id": item.get("id"),
                "name": item.get("name", "Unknown"),
                "description": item.get("description", ""),
                "type": item.get("type", "Unknown"),
                "creator": item.get("creator", {}).get("username", "Unknown"),
                "download_url": version.get("downloadUrl"),
                "images": [img.get("url") for img in version.get("images", []) if img.get("url")],
                "tags": item.get("tags", []),
                "source": "civitai"
            }
            results.append(result)

        return results

    def _parse_huggingface_results(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse HuggingFace API results."""
        results = []
        for item in items:
            result = {
                "id": item.get("id"),
                "name": item.get("id", "Unknown").split("/")[-1],
                "description": item.get("description", ""),
                "type": "checkpoint",  # Default type
                "creator": item.get("author", "Unknown"),
                "download_url": f"https://huggingface.co/{item.get('id')}/resolve/main/model.safetensors",
                "images": [],  # HuggingFace doesn't provide preview images easily
                "tags": item.get("tags", []),
                "source": "huggingface"
            }
            results.append(result)

        return results

    async def download_model(self, url: str, destination: Path, progress_callback: Optional[callable] = None) -> bool:
        """
        Download a model file.

        Args:
            url (str): Download URL
            destination (Path): Destination path
            progress_callback (callable, optional): Progress callback function

        Returns:
            bool: True if successful
        """
        if not self.session:
            return False

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)

            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Download failed: {response.status}")
                    return False

                total_size = int(response.headers.get('content-length', 0))

                with open(destination, 'wb') as f:
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)

                logger.info(f"Downloaded model to {destination}")
                return True

        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            return False


async def search_models(query: str, sources: List[str] = None, model_type: str = "checkpoint", limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search for models across multiple sources.

    Args:
        query (str): Search query
        sources (list, optional): List of sources to search
        model_type (str): Model type
        limit (int): Maximum results per source

    Returns:
        Dict with results from each source
    """
    if sources is None:
        sources = ["civitai", "huggingface"]

    results = {}

    async with ModelBrowser() as browser:
        if "civitai" in sources:
            results["civitai"] = await browser.search_civitai(query, model_type, limit)

        if "huggingface" in sources:
            results["huggingface"] = await browser.search_huggingface(query, model_type, limit)

    return results


async def download_model(url: str, destination: Path) -> bool:
    """
    Download a model file.

    Args:
        url (str): Download URL
        destination (Path): Destination path

    Returns:
        bool: True if successful
    """
    async with ModelBrowser() as browser:
        return await browser.download_model(url, destination)