"""
Style Transfer Engine
AI-powered style adaptation and transfer capabilities
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import hashlib
from pathlib import Path
import io
import base64

try:
    import torch
    import torch.nn as nn
    import torchvision.transforms as transforms
    from torchvision.models import vgg19
    from PIL import Image
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class StyleTransferMethod(Enum):
    """Style transfer methods"""
    NEURAL_STYLE_TRANSFER = "neural_style_transfer"
    ADAPTIVE_INSTANCE_NORMALIZATION = "adaptive_instance_normalization"
    STYLE_CLIP = "style_clip"
    DIFFUSION_BASED = "diffusion_based"
    FAST_STYLE_TRANSFER = "fast_style_transfer"


class StyleCategory(Enum):
    """Style categories"""
    ARTISTIC = "artistic"
    PHOTOGRAPHIC = "photographic"
    ILLUSTRATION = "illustration"
    ABSTRACT = "abstract"
    REALISTIC = "realistic"
    CARTOON = "cartoon"
    VINTAGE = "vintage"
    MODERN = "modern"


@dataclass
class StyleReference:
    """Style reference definition"""
    style_id: str
    name: str
    description: str
    category: StyleCategory
    image_data: Optional[bytes] = None
    image_path: Optional[str] = None
    style_features: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'style_id': self.style_id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'image_path': self.image_path,
            'style_features': self.style_features,
            'created_at': self.created_at.isoformat(),
            'usage_count': self.usage_count
        }


@dataclass
class StyleTransferRequest:
    """Style transfer request"""
    request_id: str
    content_image: bytes
    style_reference: Union[str, StyleReference]  # style_id or StyleReference object
    method: StyleTransferMethod = StyleTransferMethod.NEURAL_STYLE_TRANSFER
    parameters: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'request_id': self.request_id,
            'style_reference': self.style_reference if isinstance(self.style_reference, str) else self.style_reference.style_id,
            'method': self.method.value,
            'parameters': self.parameters,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class StyleTransferResult:
    """Style transfer result"""
    request_id: str
    result_image: bytes
    style_reference: str
    method: StyleTransferMethod
    parameters: Dict[str, Any]
    processing_time: float
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'request_id': self.request_id,
            'style_reference': self.style_reference,
            'method': self.method.value,
            'parameters': self.parameters,
            'processing_time': self.processing_time,
            'quality_score': self.quality_score,
            'metadata': self.metadata,
            'generated_at': self.generated_at.isoformat(),
            'success': self.success,
            'error_message': self.error_message
        }


class StyleTransferEngine:
    """AI-powered style transfer engine"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Style library
        self.style_library: Dict[str, StyleReference] = {}

        # Transfer history
        self.transfer_history: List[StyleTransferResult] = []

        # Neural network models
        self.models: Dict[str, Any] = {}

        # Caching
        self.cache: Dict[str, StyleTransferResult] = {}

        # Device configuration
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') if TORCH_AVAILABLE else None

        # Initialize default styles
        self._initialize_default_styles()

        # Load models if available
        if TORCH_AVAILABLE:
            self._load_models()

    def _initialize_default_styles(self):
        """Initialize default style references"""

        default_styles = [
            {
                'style_id': 'van_gogh_starry_night',
                'name': 'Van Gogh - Starry Night',
                'description': 'Swirling blue night sky with bright stars',
                'category': StyleCategory.ARTISTIC
            },
            {
                'style_id': 'picasso_cubism',
                'name': 'Picasso - Cubism',
                'description': 'Geometric shapes and fragmented forms',
                'category': StyleCategory.ABSTRACT
            },
            {
                'style_id': 'monet_impressionist',
                'name': 'Monet - Impressionist',
                'description': 'Light and color with loose brushwork',
                'category': StyleCategory.ARTISTIC
            },
            {
                'style_id': 'hokusai_wave',
                'name': 'Hokusai - The Great Wave',
                'description': 'Dramatic wave with Mount Fuji in background',
                'category': StyleCategory.ILLUSTRATION
            },
            {
                'style_id': 'retro_comics',
                'name': 'Retro Comics',
                'description': 'Classic comic book style with bold colors',
                'category': StyleCategory.CARTOON
            },
            {
                'style_id': 'vintage_photography',
                'name': 'Vintage Photography',
                'description': 'Sepia tones with film grain effect',
                'category': StyleCategory.VINTAGE
            }
        ]

        for style_data in default_styles:
            style = StyleReference(**style_data)
            self.style_library[style.style_id] = style

    def _load_models(self):
        """Load neural network models for style transfer"""
        try:
            # Load VGG19 for neural style transfer
            self.models['vgg19'] = vgg19(pretrained=True).features.to(self.device)
            self.models['vgg19'].eval()

            # Normalization for VGG
            self.normalize = transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )

            self.logger.info("Style transfer models loaded successfully")

        except Exception as e:
            self.logger.warning(f"Failed to load style transfer models: {e}")

    def add_style_reference(self, style: StyleReference):
        """Add a new style reference to the library"""
        self.style_library[style.style_id] = style
        self.logger.info(f"Added style reference: {style.name}")

    def get_style_reference(self, style_id: str) -> Optional[StyleReference]:
        """Get style reference by ID"""
        return self.style_library.get(style_id)

    def list_style_references(self, category: Optional[StyleCategory] = None) -> List[StyleReference]:
        """List available style references"""
        styles = list(self.style_library.values())

        if category:
            styles = [s for s in styles if s.category == category]

        # Sort by usage count (most used first)
        styles.sort(key=lambda s: s.usage_count, reverse=True)

        return styles

    async def transfer_style(self, request: StyleTransferRequest) -> StyleTransferResult:
        """Transfer style to content image"""
        start_time = asyncio.get_event_loop().time()

        try:
            # Check cache
            cache_key = self._generate_cache_key(request)
            if cache_key in self.cache:
                cached_result = self.cache[cache_key]
                if (datetime.now() - cached_result.generated_at).total_seconds() < 3600:  # 1 hour cache
                    return cached_result

            # Get style reference
            if isinstance(request.style_reference, str):
                style_ref = self.get_style_reference(request.style_reference)
                if not style_ref:
                    raise ValueError(f"Style reference not found: {request.style_reference}")
            else:
                style_ref = request.style_reference

            # Increment usage count
            style_ref.usage_count += 1

            # Route to appropriate method
            if request.method == StyleTransferMethod.NEURAL_STYLE_TRANSFER:
                result = await self._neural_style_transfer(request, style_ref)
            elif request.method == StyleTransferMethod.ADAPTIVE_INSTANCE_NORMALIZATION:
                result = await self._adaptive_instance_normalization(request, style_ref)
            elif request.method == StyleTransferMethod.FAST_STYLE_TRANSFER:
                result = await self._fast_style_transfer(request, style_ref)
            else:
                raise ValueError(f"Unsupported transfer method: {request.method}")

            # Calculate processing time
            processing_time = asyncio.get_event_loop().time() - start_time
            result.processing_time = processing_time

            # Calculate quality score (simplified)
            result.quality_score = self._calculate_quality_score(result)

            # Cache result
            self.cache[cache_key] = result

            # Add to history
            self.transfer_history.append(result)

            # Keep history limited
            if len(self.transfer_history) > 500:
                self.transfer_history = self.transfer_history[-500:]

            return result

        except Exception as e:
            self.logger.error(f"Style transfer failed: {e}")
            processing_time = asyncio.get_event_loop().time() - start_time

            return StyleTransferResult(
                request_id=request.request_id,
                result_image=request.content_image,  # Return original on failure
                style_reference=request.style_reference if isinstance(request.style_reference, str) else request.style_reference.style_id,
                method=request.method,
                parameters=request.parameters,
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )

    async def _neural_style_transfer(self, request: StyleTransferRequest, style_ref: StyleReference) -> StyleTransferResult:
        """Perform neural style transfer"""
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available for neural style transfer")

        # Load images
        content_image = self._load_image_from_bytes(request.content_image)
        style_image = self._load_style_image(style_ref)

        # Perform style transfer
        result_tensor = await self._neural_style_transfer_impl(
            content_image, style_image, request.parameters
        )

        # Convert back to bytes
        result_image = self._tensor_to_bytes(result_tensor)

        return StyleTransferResult(
            request_id=request.request_id,
            result_image=result_image,
            style_reference=style_ref.style_id,
            method=StyleTransferMethod.NEURAL_STYLE_TRANSFER,
            parameters=request.parameters,
            processing_time=0.0,  # Will be set by caller
            metadata={
                'content_size': content_image.size,
                'style_name': style_ref.name
            }
        )

    async def _neural_style_transfer_impl(self, content_img: Image.Image, style_img: Image.Image,
                                        params: Dict[str, Any]) -> torch.Tensor:
        """Neural style transfer implementation"""
        # Convert to tensors
        content_tensor = self._image_to_tensor(content_img).to(self.device)
        style_tensor = self._image_to_tensor(style_img).to(self.device)

        # Style transfer parameters
        num_steps = params.get('num_steps', 300)
        style_weight = params.get('style_weight', 1000000)
        content_weight = params.get('content_weight', 1)

        # Initialize with content image
        input_tensor = content_tensor.clone().requires_grad_(True)

        optimizer = torch.optim.LBFGS([input_tensor])

        # Extract features
        content_features = self._get_features(content_tensor, ['conv4_2'])
        style_features = self._get_features(style_tensor, ['conv1_1', 'conv2_1', 'conv3_1', 'conv4_1', 'conv5_1'])
        style_grams = {layer: self._gram_matrix(style_features[layer]) for layer in style_features}

        def closure():
            optimizer.zero_grad()

            input_features = self._get_features(input_tensor, ['conv4_2'] + list(style_features.keys()))

            # Content loss
            content_loss = torch.mean((input_features['conv4_2'] - content_features['conv4_2']) ** 2)

            # Style loss
            style_loss = 0
            for layer in style_features:
                input_gram = self._gram_matrix(input_features[layer])
                style_gram = style_grams[layer]
                layer_loss = torch.mean((input_gram - style_gram) ** 2)
                style_loss += layer_loss

            total_loss = content_weight * content_loss + style_weight * style_loss
            total_loss.backward()

            return total_loss

        # Optimization loop
        for i in range(num_steps):
            optimizer.step(closure)

        # Clamp values
        input_tensor.data.clamp_(0, 1)

        return input_tensor

    async def _adaptive_instance_normalization(self, request: StyleTransferRequest, style_ref: StyleReference) -> StyleTransferResult:
        """Perform AdaIN style transfer"""
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available for AdaIN")

        # Simplified AdaIN implementation
        content_image = self._load_image_from_bytes(request.content_image)
        style_image = self._load_style_image(style_ref)

        content_tensor = self._image_to_tensor(content_image).to(self.device)
        style_tensor = self._image_to_tensor(style_image).to(self.device)

        # AdaIN transformation
        result_tensor = self._adain_impl(content_tensor, style_tensor)

        result_image = self._tensor_to_bytes(result_tensor)

        return StyleTransferResult(
            request_id=request.request_id,
            result_image=result_image,
            style_reference=style_ref.style_id,
            method=StyleTransferMethod.ADAPTIVE_INSTANCE_NORMALIZATION,
            parameters=request.parameters,
            processing_time=0.0,
            metadata={'method': 'AdaIN'}
        )

    def _adain_impl(self, content: torch.Tensor, style: torch.Tensor) -> torch.Tensor:
        """AdaIN implementation"""
        # Calculate mean and std
        content_mean, content_std = self._calc_mean_std(content)
        style_mean, style_std = self._calc_mean_std(style)

        # AdaIN transformation
        result = style_std * ((content - content_mean) / content_std) + style_mean

        return result

    def _calc_mean_std(self, tensor: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Calculate mean and standard deviation"""
        batch_size, channels = tensor.shape[:2]
        mean = tensor.view(batch_size, channels, -1).mean(dim=2)
        std = tensor.view(batch_size, channels, -1).std(dim=2)
        return mean, std

    async def _fast_style_transfer(self, request: StyleTransferRequest, style_ref: StyleReference) -> StyleTransferResult:
        """Perform fast style transfer using pre-trained models"""
        # Placeholder for fast style transfer
        # In a real implementation, this would use pre-trained transformer models
        raise NotImplementedError("Fast style transfer not yet implemented")

    def _load_image_from_bytes(self, image_bytes: bytes) -> Image.Image:
        """Load image from bytes"""
        return Image.open(io.BytesIO(image_bytes)).convert('RGB')

    def _load_style_image(self, style_ref: StyleReference) -> Image.Image:
        """Load style reference image"""
        if style_ref.image_data:
            return self._load_image_from_bytes(style_ref.image_data)
        elif style_ref.image_path:
            return Image.open(style_ref.image_path).convert('RGB')
        else:
            raise ValueError(f"No image data available for style: {style_ref.style_id}")

    def _image_to_tensor(self, image: Image.Image) -> torch.Tensor:
        """Convert PIL image to tensor"""
        transform = transforms.Compose([
            transforms.Resize(512),
            transforms.ToTensor(),
            self.normalize
        ])
        return transform(image).unsqueeze(0)

    def _tensor_to_bytes(self, tensor: torch.Tensor) -> bytes:
        """Convert tensor to image bytes"""
        # Denormalize
        mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).to(tensor.device)
        std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).to(tensor.device)

        tensor = tensor * std + mean
        tensor = torch.clamp(tensor, 0, 1)

        # Convert to PIL
        to_pil = transforms.ToPILImage()
        image = to_pil(tensor.squeeze(0).cpu())

        # Save to bytes
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()

    def _get_features(self, tensor: torch.Tensor, layers: List[str]) -> Dict[str, torch.Tensor]:
        """Extract features from VGG network"""
        features = {}
        x = tensor

        layer_mapping = {
            'conv1_1': 0, 'conv1_2': 2,
            'conv2_1': 5, 'conv2_2': 7,
            'conv3_1': 10, 'conv3_2': 12, 'conv3_3': 14,
            'conv4_1': 17, 'conv4_2': 19, 'conv4_3': 21,
            'conv5_1': 24, 'conv5_2': 26, 'conv5_3': 28
        }

        for layer_name in layers:
            if layer_name in layer_mapping:
                layer_idx = layer_mapping[layer_name]
                for i in range(layer_idx + 1):
                    x = self.models['vgg19'][i](x)
                features[layer_name] = x

        return features

    def _gram_matrix(self, tensor: torch.Tensor) -> torch.Tensor:
        """Calculate Gram matrix"""
        batch_size, channels, height, width = tensor.size()
        features = tensor.view(batch_size * channels, height * width)
        gram = torch.mm(features, features.t())
        return gram.div(batch_size * channels * height * width)

    def _calculate_quality_score(self, result: StyleTransferResult) -> float:
        """Calculate quality score for style transfer result"""
        # Simplified quality scoring
        # In a real implementation, this would use more sophisticated metrics
        base_score = 0.8

        # Adjust based on processing time (faster = better, but not too fast)
        if result.processing_time < 10:
            base_score += 0.1
        elif result.processing_time > 300:
            base_score -= 0.2

        # Adjust based on method
        method_scores = {
            StyleTransferMethod.NEURAL_STYLE_TRANSFER: 0.1,
            StyleTransferMethod.ADAPTIVE_INSTANCE_NORMALIZATION: 0.05,
            StyleTransferMethod.FAST_STYLE_TRANSFER: 0.0
        }
        base_score += method_scores.get(result.method, 0.0)

        return max(0.0, min(1.0, base_score))

    def _generate_cache_key(self, request: StyleTransferRequest) -> str:
        """Generate cache key for request"""
        style_id = request.style_reference if isinstance(request.style_reference, str) else request.style_reference.style_id
        key_data = f"{request.method.value}:{style_id}:{hashlib.md5(request.content_image).hexdigest()}:{json.dumps(request.parameters, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_transfer_history(self, user_id: Optional[str] = None, limit: int = 50) -> List[StyleTransferResult]:
        """Get style transfer history"""
        history = self.transfer_history

        if user_id:
            # Filter by user (would need proper user tracking)
            pass

        return history[-limit:]

    def get_style_statistics(self) -> Dict[str, Any]:
        """Get statistics about style usage"""
        total_transfers = len(self.transfer_history)
        style_usage = {}

        for result in self.transfer_history:
            style_id = result.style_reference
            if style_id not in style_usage:
                style_usage[style_id] = 0
            style_usage[style_id] += 1

        return {
            'total_transfers': total_transfers,
            'style_usage': style_usage,
            'cache_size': len(self.cache),
            'library_size': len(self.style_library)
        }


# Global instance
_style_transfer_engine = None

def get_style_transfer_engine() -> StyleTransferEngine:
    """Get global style transfer engine instance"""
    global _style_transfer_engine
    if _style_transfer_engine is None:
        _style_transfer_engine = StyleTransferEngine()
    return _style_transfer_engine

async def initialize_style_transfer_engine() -> StyleTransferEngine:
    """Initialize the global style transfer engine"""
    global _style_transfer_engine
    if _style_transfer_engine is None:
        _style_transfer_engine = StyleTransferEngine()
    return _style_transfer_engine</content>
