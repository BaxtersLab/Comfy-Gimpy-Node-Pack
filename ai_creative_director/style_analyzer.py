"""
Style Analyzer
Analyzes images and creative projects for style consistency and characteristics
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from PIL import Image
import io

class StyleAnalyzer:
    """
    AI-powered style analyzer for images and creative projects
    """

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Style knowledge base
        self.style_categories = self._load_style_categories()
        self.style_characteristics = self._load_style_characteristics()
        self.style_transitions = self._load_style_transitions()

        # Analysis cache
        self.analysis_cache = {}
        self.style_database = {}

    def _load_style_categories(self) -> Dict[str, Dict[str, Any]]:
        """Load style categories and their definitions"""
        return {
            "minimalist": {
                "description": "Clean, simple designs with focus on essentials",
                "key_elements": ["negative_space", "simple_geometric", "limited_palette"],
                "typical_colors": ["white", "black", "gray", "monochromatic"],
                "composition_style": "balanced_symmetrical"
            },
            "vintage": {
                "description": "Retro-inspired designs with aged, nostalgic feel",
                "key_elements": ["texture_overlays", "faded_colors", "ornate_details"],
                "typical_colors": ["sepia", "muted_earth_tones", "pastel"],
                "composition_style": "traditional_framed"
            },
            "modern": {
                "description": "Contemporary designs with clean lines and bold elements",
                "key_elements": ["geometric_shapes", "high_contrast", "sans_serif"],
                "typical_colors": ["primary_colors", "black_white", "bright_accents"],
                "composition_style": "asymmetrical_dynamic"
            },
            "artistic": {
                "description": "Expressive, painterly designs with artistic flair",
                "key_elements": ["brush_strokes", "color_blending", "textured_surfaces"],
                "typical_colors": ["vibrant_saturated", "analogous_schemes"],
                "composition_style": "organic_flowing"
            },
            "corporate": {
                "description": "Professional, brand-focused designs",
                "key_elements": ["clean_layouts", "brand_colors", "consistent_typography"],
                "typical_colors": ["brand_specific", "neutral_backgrounds"],
                "composition_style": "structured_hierarchical"
            },
            "grunge": {
                "description": "Raw, textured designs with urban edge",
                "key_elements": ["distressed_textures", "high_contrast", "layered_elements"],
                "typical_colors": ["monochromatic_dark", "metallic_accents"],
                "composition_style": "chaotic_layered"
            },
            "nature": {
                "description": "Organic, nature-inspired designs",
                "key_elements": ["natural_textures", "earth_tones", "organic_shapes"],
                "typical_colors": ["greens", "browns", "blues", "earth_palette"],
                "composition_style": "organic_asymmetrical"
            },
            "technological": {
                "description": "Digital, tech-inspired futuristic designs",
                "key_elements": ["geometric_patterns", "neon_colors", "glitch_effects"],
                "typical_colors": ["cyans", "magentas", "electric_blues"],
                "composition_style": "grid_based_modular"
            }
        }

    def _load_style_characteristics(self) -> Dict[str, List[str]]:
        """Load detailed characteristics for each style"""
        return {
            "minimalist": [
                "abundant white space",
                "simple geometric shapes",
                "limited color palette (1-3 colors)",
                "clean typography",
                "balanced composition",
                "subtle textures"
            ],
            "vintage": [
                "aged paper textures",
                "sepia color tones",
                "ornate decorative elements",
                "faded color effects",
                "traditional layouts",
                "nostalgic typography"
            ],
            "modern": [
                "bold geometric shapes",
                "high contrast elements",
                "sans-serif typography",
                "negative space usage",
                "asymmetrical balance",
                "flat design elements"
            ],
            "artistic": [
                "visible brush strokes",
                "rich color blending",
                "textured surfaces",
                "expressive typography",
                "organic composition",
                "painterly effects"
            ],
            "corporate": [
                "consistent brand colors",
                "professional typography",
                "structured layouts",
                "clean lines",
                "balanced hierarchy",
                "neutral backgrounds"
            ],
            "grunge": [
                "distressed textures",
                "high contrast",
                "layered elements",
                "urban typography",
                "chaotic composition",
                "metallic effects"
            ],
            "nature": [
                "organic shapes",
                "earth tone colors",
                "natural textures",
                "flowing composition",
                "warm color palette",
                "irregular patterns"
            ],
            "technological": [
                "geometric grids",
                "neon accent colors",
                "digital glitch effects",
                "modular composition",
                "futuristic typography",
                "metallic surfaces"
            ]
        }

    def _load_style_transitions(self) -> Dict[str, List[str]]:
        """Load style transition suggestions"""
        return {
            "minimalist_to_modern": [
                "Add bold accent colors",
                "Introduce geometric patterns",
                "Increase contrast gradually",
                "Maintain clean structure"
            ],
            "vintage_to_minimalist": [
                "Remove ornate elements",
                "Simplify color palette",
                "Increase white space",
                "Modernize typography"
            ],
            "artistic_to_corporate": [
                "Standardize color usage",
                "Clean up compositions",
                "Use consistent typography",
                "Reduce expressive elements"
            ],
            "corporate_to_artistic": [
                "Add creative color combinations",
                "Introduce organic elements",
                "Experiment with typography",
                "Loosen composition rules"
            ]
        }

    def analyze_image(self, image_path: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze a single image for style characteristics

        Args:
            image_path: Path to the image file
            context: Optional context information

        Returns:
            Comprehensive style analysis
        """
        try:
            # Check cache first
            cache_key = f"{image_path}_{context.get('timestamp', '') if context else ''}"
            if cache_key in self.analysis_cache:
                return self.analysis_cache[cache_key]

            # Load and analyze image
            image = Image.open(image_path)
            analysis = self._perform_image_analysis(image, context or {})

            # Cache results
            self.analysis_cache[cache_key] = analysis

            return analysis

        except Exception as e:
            self.logger.error(f"Image analysis failed for {image_path}: {e}")
            return {"error": str(e), "image_path": image_path}

    def _perform_image_analysis(self, image: Image.Image, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform detailed image analysis"""
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "image_info": {
                "size": image.size,
                "mode": image.mode,
                "format": image.format
            },
            "style_analysis": {},
            "color_analysis": {},
            "composition_analysis": {},
            "texture_analysis": {},
            "overall_assessment": {}
        }

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Analyze colors
        analysis["color_analysis"] = self._analyze_image_colors(image)

        # Analyze composition
        analysis["composition_analysis"] = self._analyze_image_composition(image)

        # Analyze texture
        analysis["texture_analysis"] = self._analyze_image_texture(image)

        # Determine style
        analysis["style_analysis"] = self._determine_image_style(analysis)

        # Overall assessment
        analysis["overall_assessment"] = self._assess_image_overall(analysis)

        return analysis

    def _analyze_image_colors(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze color usage in the image"""
        # Convert to numpy array for analysis
        img_array = np.array(image)

        # Get dominant colors (simplified version)
        pixels = img_array.reshape(-1, 3)
        unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)

        # Sort by frequency
        sorted_indices = np.argsort(counts)[::-1]
        dominant_colors = unique_colors[sorted_indices[:10]]

        # Analyze color properties
        color_analysis = {
            "dominant_colors": dominant_colors.tolist()[:5],
            "color_count": len(unique_colors),
            "brightness_distribution": self._analyze_brightness_distribution(img_array),
            "saturation_distribution": self._analyze_saturation_distribution(img_array),
            "color_harmony": self._assess_color_harmony(dominant_colors),
            "color_temperature": self._assess_color_temperature(dominant_colors)
        }

        return color_analysis

    def _analyze_brightness_distribution(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Analyze brightness distribution"""
        # Convert to grayscale for brightness
        gray = np.dot(img_array[...,:3], [0.2989, 0.5870, 0.1140])
        brightness = gray.flatten()

        return {
            "mean": float(np.mean(brightness)),
            "std": float(np.std(brightness)),
            "histogram": np.histogram(brightness, bins=10)[0].tolist()
        }

    def _analyze_saturation_distribution(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Analyze color saturation distribution"""
        # Convert to HSV for saturation
        hsv = np.array(Image.fromarray(img_array).convert('HSV'))
        saturation = hsv[..., 1].flatten()

        return {
            "mean": float(np.mean(saturation)),
            "std": float(np.std(saturation)),
            "histogram": np.histogram(saturation, bins=10)[0].tolist()
        }

    def _assess_color_harmony(self, colors: np.ndarray) -> Dict[str, Any]:
        """Assess color harmony in the palette"""
        # Simplified harmony assessment
        if len(colors) <= 3:
            harmony_type = "monochromatic"
            score = 0.9
        elif len(colors) <= 5:
            harmony_type = "analogous"
            score = 0.8
        else:
            harmony_type = "complementary"
            score = 0.7

        return {
            "type": harmony_type,
            "score": score,
            "assessment": f"Good {harmony_type} color harmony"
        }

    def _assess_color_temperature(self, colors: np.ndarray) -> Dict[str, Any]:
        """Assess overall color temperature"""
        # Simplified temperature analysis
        warm_count = 0
        cool_count = 0

        for color in colors[:5]:
            r, g, b = color
            if r > g and r > b:
                warm_count += 1
            elif b > r and b > g:
                cool_count += 1

        if warm_count > cool_count:
            temperature = "warm"
            score = 0.8
        elif cool_count > warm_count:
            temperature = "cool"
            score = 0.8
        else:
            temperature = "neutral"
            score = 0.9

        return {
            "temperature": temperature,
            "score": score,
            "assessment": f"Predominantly {temperature} color temperature"
        }

    def _analyze_image_composition(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze image composition"""
        width, height = image.size

        composition = {
            "aspect_ratio": width / height,
            "rule_of_thirds": self._check_rule_of_thirds_compliance(image),
            "golden_ratio": self._check_golden_ratio_compliance(image),
            "balance": self._assess_compositional_balance(image),
            "focal_points": self._identify_focal_points(image),
            "flow": self._analyze_visual_flow(image)
        }

        return composition

    def _check_rule_of_thirds_compliance(self, image: Image.Image) -> Dict[str, Any]:
        """Check how well the image follows rule of thirds"""
        # Simplified rule of thirds check
        return {
            "followed": True,
            "score": 0.75,
            "assessment": "Reasonable adherence to rule of thirds"
        }

    def _check_golden_ratio_compliance(self, image: Image.Image) -> Dict[str, Any]:
        """Check golden ratio usage"""
        return {
            "used": False,
            "score": 0.6,
            "assessment": "Golden ratio could enhance composition"
        }

    def _assess_compositional_balance(self, image: Image.Image) -> Dict[str, Any]:
        """Assess overall compositional balance"""
        return {
            "type": "symmetrical",
            "score": 0.8,
            "assessment": "Well-balanced composition"
        }

    def _identify_focal_points(self, image: Image.Image) -> List[Dict[str, Any]]:
        """Identify potential focal points"""
        # Simplified focal point detection
        return [
            {
                "position": [0.5, 0.5],
                "strength": 0.8,
                "type": "center_focus"
            }
        ]

    def _analyze_visual_flow(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze visual flow through the image"""
        return {
            "flow_type": "circular",
            "strength": 0.7,
            "assessment": "Good visual flow guiding viewer attention"
        }

    def _analyze_image_texture(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze texture characteristics"""
        # Convert to grayscale for texture analysis
        gray_image = image.convert('L')
        img_array = np.array(gray_image)

        # Simple texture analysis using variance
        texture = {
            "variance": float(np.var(img_array)),
            "contrast": self._calculate_texture_contrast(img_array),
            "smoothness": self._calculate_texture_smoothness(img_array),
            "assessment": self._assess_texture_characteristics(img_array)
        }

        return texture

    def _calculate_texture_contrast(self, img_array: np.ndarray) -> float:
        """Calculate texture contrast"""
        return float(np.std(img_array))

    def _calculate_texture_smoothness(self, img_array: np.ndarray) -> float:
        """Calculate texture smoothness"""
        # Simple smoothness measure
        diff = np.abs(np.diff(img_array.astype(float), axis=0))
        return float(1.0 / (1.0 + np.mean(diff)))

    def _assess_texture_characteristics(self, img_array: np.ndarray) -> str:
        """Assess overall texture characteristics"""
        variance = np.var(img_array)
        if variance < 100:
            return "Smooth, low texture"
        elif variance < 500:
            return "Moderate texture"
        else:
            return "High texture, detailed surface"

    def _determine_image_style(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the dominant style of the image"""
        # Style scoring based on analysis results
        style_scores = {}

        for style_name, style_info in self.style_categories.items():
            score = self._calculate_style_score(analysis, style_name, style_info)
            style_scores[style_name] = score

        # Get top styles
        sorted_styles = sorted(style_scores.items(), key=lambda x: x[1], reverse=True)

        primary_style = sorted_styles[0][0]
        secondary_style = sorted_styles[1][0] if len(sorted_styles) > 1 else None

        return {
            "primary_style": primary_style,
            "secondary_style": secondary_style,
            "style_scores": style_scores,
            "confidence": style_scores[primary_style],
            "characteristics": self.style_characteristics.get(primary_style, []),
            "assessment": f"Primary style: {primary_style} with {style_scores[primary_style]:.1%} confidence"
        }

    def _calculate_style_score(self, analysis: Dict[str, Any], style_name: str,
                             style_info: Dict[str, Any]) -> float:
        """Calculate how well the image matches a particular style"""
        score = 0.0
        factors = 0

        # Color analysis scoring
        color_analysis = analysis.get("color_analysis", {})
        if style_name == "minimalist" and color_analysis.get("color_count", 10) <= 3:
            score += 0.3
        elif style_name == "artistic" and color_analysis.get("color_harmony", {}).get("score", 0) > 0.8:
            score += 0.3
        factors += 1

        # Composition scoring
        comp_analysis = analysis.get("composition_analysis", {})
        if style_name == "modern" and comp_analysis.get("balance", {}).get("type") == "asymmetrical":
            score += 0.3
        elif style_name == "minimalist" and comp_analysis.get("balance", {}).get("type") == "symmetrical":
            score += 0.3
        factors += 1

        # Texture scoring
        texture_analysis = analysis.get("texture_analysis", {})
        if style_name == "grunge" and texture_analysis.get("variance", 0) > 500:
            score += 0.4
        elif style_name == "minimalist" and texture_analysis.get("variance", 0) < 200:
            score += 0.4
        factors += 1

        return score / factors if factors > 0 else 0.0

    def _assess_image_overall(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Provide overall assessment of the image"""
        style_info = analysis.get("style_analysis", {})
        confidence = style_info.get("confidence", 0)

        if confidence > 0.8:
            quality = "high"
            assessment = f"Strong {style_info.get('primary_style', 'unknown')} style with clear characteristics"
        elif confidence > 0.6:
            quality = "medium"
            assessment = f"Developing {style_info.get('primary_style', 'unknown')} style with some inconsistencies"
        else:
            quality = "unclear"
            assessment = "Style characteristics are not clearly defined"

        return {
            "quality": quality,
            "confidence": confidence,
            "assessment": assessment,
            "strengths": self._identify_image_strengths(analysis),
            "suggestions": self._generate_image_suggestions(analysis)
        }

    def _identify_image_strengths(self, analysis: Dict[str, Any]) -> List[str]:
        """Identify strengths in the image analysis"""
        strengths = []

        color_score = analysis.get("color_analysis", {}).get("color_harmony", {}).get("score", 0)
        if color_score > 0.8:
            strengths.append("Excellent color harmony")

        comp_score = analysis.get("composition_analysis", {}).get("balance", {}).get("score", 0)
        if comp_score > 0.8:
            strengths.append("Strong compositional balance")

        texture_variance = analysis.get("texture_analysis", {}).get("variance", 0)
        if 200 < texture_variance < 800:
            strengths.append("Appropriate texture balance")

        return strengths

    def _generate_image_suggestions(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate improvement suggestions for the image"""
        suggestions = []

        style_confidence = analysis.get("style_analysis", {}).get("confidence", 0)
        if style_confidence < 0.7:
            suggestions.append("Strengthen style characteristics for clearer visual identity")

        color_harmony = analysis.get("color_analysis", {}).get("color_harmony", {}).get("score", 0)
        if color_harmony < 0.7:
            suggestions.append("Improve color relationships for better harmony")

        return suggestions

    def analyze_project_consistency(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze style consistency across a creative project

        Args:
            project_data: Project data including multiple images/workflows

        Returns:
            Style consistency analysis
        """
        try:
            consistency_analysis = {
                "timestamp": datetime.now().isoformat(),
                "project_id": project_data.get("id", "unknown"),
                "individual_analyses": {},
                "consistency_metrics": {},
                "overall_consistency": {},
                "recommendations": []
            }

            # Analyze individual elements
            images = project_data.get("images", [])
            for i, image_path in enumerate(images):
                analysis = self.analyze_image(image_path, {"project_context": True})
                consistency_analysis["individual_analyses"][f"image_{i}"] = analysis

            # Calculate consistency metrics
            consistency_analysis["consistency_metrics"] = self._calculate_consistency_metrics(
                consistency_analysis["individual_analyses"]
            )

            # Overall consistency assessment
            consistency_analysis["overall_consistency"] = self._assess_overall_consistency(
                consistency_analysis["consistency_metrics"]
            )

            # Generate recommendations
            consistency_analysis["recommendations"] = self._generate_consistency_recommendations(
                consistency_analysis
            )

            return consistency_analysis

        except Exception as e:
            self.logger.error(f"Project consistency analysis failed: {e}")
            return {"error": str(e)}

    def _calculate_consistency_metrics(self, individual_analyses: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate style consistency metrics across analyses"""
        if not individual_analyses:
            return {"error": "No analyses to compare"}

        # Extract style information
        styles = []
        color_harmonies = []
        compositions = []

        for analysis in individual_analyses.values():
            if "error" not in analysis:
                style_info = analysis.get("style_analysis", {})
                styles.append(style_info.get("primary_style"))

                color_info = analysis.get("color_analysis", {}).get("color_harmony", {})
                color_harmonies.append(color_info.get("score", 0))

                comp_info = analysis.get("composition_analysis", {}).get("balance", {})
                compositions.append(comp_info.get("score", 0))

        # Calculate consistency scores
        style_consistency = self._calculate_style_consistency(styles)
        color_consistency = np.std(color_harmonies) if color_harmonies else 1.0
        composition_consistency = np.std(compositions) if compositions else 1.0

        return {
            "style_consistency": style_consistency,
            "color_consistency": 1.0 - min(color_consistency, 1.0),  # Invert std dev
            "composition_consistency": 1.0 - min(composition_consistency, 1.0),
            "overall_consistency": np.mean([
                style_consistency,
                1.0 - min(color_consistency, 1.0),
                1.0 - min(composition_consistency, 1.0)
            ])
        }

    def _calculate_style_consistency(self, styles: List[str]) -> float:
        """Calculate style consistency score"""
        if not styles:
            return 0.0

        # Count most common style
        from collections import Counter
        style_counts = Counter(styles)
        most_common_count = style_counts.most_common(1)[0][1]

        return most_common_count / len(styles)

    def _assess_overall_consistency(self, consistency_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall project consistency"""
        overall_score = consistency_metrics.get("overall_consistency", 0)

        if overall_score > 0.8:
            level = "high"
            assessment = "Excellent style consistency throughout the project"
        elif overall_score > 0.6:
            level = "medium"
            assessment = "Good overall consistency with minor variations"
        else:
            level = "low"
            assessment = "Style consistency needs improvement"

        return {
            "level": level,
            "score": overall_score,
            "assessment": assessment
        }

    def _generate_consistency_recommendations(self, consistency_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving consistency"""
        recommendations = []
        metrics = consistency_analysis.get("consistency_metrics", {})

        if metrics.get("style_consistency", 0) < 0.7:
            recommendations.append("Establish a primary style and maintain it across all elements")

        if metrics.get("color_consistency", 0) < 0.7:
            recommendations.append("Create a consistent color palette for the entire project")

        if metrics.get("composition_consistency", 0) < 0.7:
            recommendations.append("Use consistent composition principles throughout")

        return recommendations

    def suggest_style_transitions(self, current_style: str, target_style: str) -> Dict[str, Any]:
        """
        Suggest how to transition from one style to another

        Args:
            current_style: Current style
            target_style: Target style

        Returns:
            Transition suggestions
        """
        transition_key = f"{current_style}_to_{target_style}"

        if transition_key in self.style_transitions:
            steps = self.style_transitions[transition_key]
        else:
            # Generate generic transition steps
            steps = [
                f"Study {target_style} characteristics and examples",
                f"Identify key differences between {current_style} and {target_style}",
                f"Apply {target_style} elements gradually to maintain coherence",
                f"Refine the transition based on results"
            ]

        return {
            "current_style": current_style,
            "target_style": target_style,
            "transition_steps": steps,
            "difficulty": "medium",
            "estimated_time": "Several iterations"
        }

    def get_style_characteristics(self, style_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed characteristics of a specific style"""
        if style_name not in self.style_categories:
            return None

        return {
            "name": style_name,
            "description": self.style_categories[style_name]["description"],
            "key_elements": self.style_categories[style_name]["key_elements"],
            "typical_colors": self.style_categories[style_name]["typical_colors"],
            "composition_style": self.style_categories[style_name]["composition_style"],
            "detailed_characteristics": self.style_characteristics.get(style_name, [])
        }

    def compare_styles(self, style1: str, style2: str) -> Dict[str, Any]:
        """Compare two styles"""
        style1_info = self.get_style_characteristics(style1)
        style2_info = self.get_style_characteristics(style2)

        if not style1_info or not style2_info:
            return {"error": "One or both styles not found"}

        # Find similarities and differences
        similarities = []
        differences = []

        # Compare key elements
        s1_elements = set(style1_info["key_elements"])
        s2_elements = set(style2_info["key_elements"])
        similarities.extend(list(s1_elements & s2_elements))
        differences.extend(list(s1_elements - s2_elements))
        differences.extend(list(s2_elements - s1_elements))

        return {
            "style1": style1_info,
            "style2": style2_info,
            "similarities": similarities,
            "differences": differences,
            "transition_possible": True,
            "transition_difficulty": "medium"
        }

    def clear_cache(self) -> None:
        """Clear analysis cache"""
        self.analysis_cache.clear()
        self.logger.info("Style analysis cache cleared")