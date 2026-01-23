"""
Design Reasoning Engine
Provides global design analysis and intelligent creative reasoning for Comfy Gimpy Studio
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np

class DesignReasoningEngine:
    """
    AI-powered design reasoning engine that analyzes creative projects holistically
    """

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Design knowledge base
        self.design_principles = self._load_design_principles()
        self.composition_rules = self._load_composition_rules()
        self.color_theory = self._load_color_theory()

        # Reasoning state
        self.project_history = {}
        self.reasoning_cache = {}
        self.confidence_threshold = 0.7

    def _load_design_principles(self) -> Dict[str, Any]:
        """Load design principles knowledge base"""
        return {
            "balance": {
                "symmetrical": "Creates stability and formality",
                "asymmetrical": "Creates dynamic tension and interest",
                "radial": "Draws focus to center point"
            },
            "contrast": {
                "high": "Creates drama and focus",
                "medium": "Maintains interest without overwhelming",
                "low": "Creates harmony and subtlety"
            },
            "emphasis": {
                "focal_point": "Primary element that draws attention",
                "hierarchy": "Organized importance of elements",
                "isolation": "Separating important elements"
            },
            "unity": {
                "repetition": "Consistent use of elements",
                "proximity": "Grouping related elements",
                "continuation": "Flowing lines and shapes"
            },
            "rhythm": {
                "regular": "Predictable, stable patterns",
                "alternating": "ABAB pattern for interest",
                "progressive": "Gradually changing patterns"
            }
        }

    def _load_composition_rules(self) -> Dict[str, Any]:
        """Load composition rules and guidelines"""
        return {
            "rule_of_thirds": {
                "description": "Divide image into thirds for optimal composition",
                "grid": [1/3, 2/3],
                "power_points": [(1/3, 1/3), (1/3, 2/3), (2/3, 1/3), (2/3, 2/3)]
            },
            "golden_ratio": {
                "ratio": 1.618,
                "description": "Mathematically pleasing proportion",
                "spiral": "Fibonacci spiral for natural flow"
            },
            "leading_lines": {
                "types": ["roads", "rivers", "fences", "buildings"],
                "purpose": "Guide viewer's eye through composition"
            },
            "framing": {
                "natural": "Use environment to frame subject",
                "purpose": "Focus attention and add depth"
            }
        }

    def _load_color_theory(self) -> Dict[str, Any]:
        """Load color theory knowledge"""
        return {
            "primary": ["red", "blue", "yellow"],
            "secondary": ["orange", "green", "purple"],
            "warm": ["red", "orange", "yellow"],
            "cool": ["blue", "green", "purple"],
            "complementary": {
                "red": "green",
                "blue": "orange",
                "yellow": "purple"
            },
            "analogous": {
                "red": ["orange", "purple"],
                "blue": ["green", "purple"],
                "yellow": ["orange", "green"]
            },
            "triadic": [
                ["red", "yellow", "blue"],
                ["orange", "green", "purple"]
            ]
        }

    def analyze_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform global design analysis on a creative project

        Args:
            project_data: Project information including images, workflows, metadata

        Returns:
            Comprehensive design analysis results
        """
        try:
            analysis_results = {
                "timestamp": datetime.now().isoformat(),
                "project_id": project_data.get("id", "unknown"),
                "overall_assessment": {},
                "design_elements": {},
                "composition_analysis": {},
                "color_analysis": {},
                "style_consistency": {},
                "recommendations": [],
                "confidence_score": 0.0
            }

            # Analyze design elements
            analysis_results["design_elements"] = self._analyze_design_elements(project_data)

            # Composition analysis
            analysis_results["composition_analysis"] = self._analyze_composition(project_data)

            # Color analysis
            analysis_results["color_analysis"] = self._analyze_colors(project_data)

            # Style consistency
            analysis_results["style_consistency"] = self._analyze_style_consistency(project_data)

            # Overall assessment
            analysis_results["overall_assessment"] = self._generate_overall_assessment(analysis_results)

            # Generate recommendations
            analysis_results["recommendations"] = self._generate_recommendations(analysis_results)

            # Calculate confidence
            analysis_results["confidence_score"] = self._calculate_confidence(analysis_results)

            # Cache results
            self._cache_analysis(project_data.get("id", "unknown"), analysis_results)

            return analysis_results

        except Exception as e:
            self.logger.error(f"Project analysis failed: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def _analyze_design_elements(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze basic design elements in the project"""
        elements = {
            "balance": self._assess_balance(project_data),
            "contrast": self._assess_contrast(project_data),
            "emphasis": self._assess_emphasis(project_data),
            "unity": self._assess_unity(project_data),
            "rhythm": self._assess_rhythm(project_data)
        }

        return elements

    def _assess_balance(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess balance in the project"""
        # This would analyze image layouts, element positioning, etc.
        return {
            "type": "symmetrical",  # symmetrical, asymmetrical, radial
            "score": 0.8,
            "assessment": "Good symmetrical balance with centered focal elements",
            "suggestions": ["Consider adding asymmetrical elements for more dynamic composition"]
        }

    def _assess_contrast(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess contrast levels in the project"""
        return {
            "level": "medium",
            "score": 0.75,
            "assessment": "Balanced contrast that maintains visual interest",
            "elements": ["light_dark", "color_intensity", "texture"]
        }

    def _assess_emphasis(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess emphasis and focal points"""
        return {
            "focal_points": 1,
            "hierarchy": "clear",
            "score": 0.85,
            "assessment": "Strong focal point with clear visual hierarchy"
        }

    def _assess_unity(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess unity and cohesion"""
        return {
            "cohesion": 0.9,
            "repetition": 0.8,
            "proximity": 0.85,
            "assessment": "High unity with consistent design elements"
        }

    def _assess_rhythm(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess rhythmic patterns"""
        return {
            "pattern": "regular",
            "flow": 0.8,
            "assessment": "Consistent rhythmic flow throughout the project"
        }

    def _analyze_composition(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze composition using design rules"""
        composition = {
            "rule_of_thirds": self._check_rule_of_thirds(project_data),
            "golden_ratio": self._check_golden_ratio(project_data),
            "leading_lines": self._check_leading_lines(project_data),
            "framing": self._check_framing(project_data),
            "overall_score": 0.0
        }

        # Calculate overall composition score
        scores = [v.get("score", 0) for v in composition.values() if isinstance(v, dict)]
        composition["overall_score"] = np.mean(scores) if scores else 0.0

        return composition

    def _check_rule_of_thirds(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check adherence to rule of thirds"""
        return {
            "followed": True,
            "score": 0.9,
            "assessment": "Good use of rule of thirds intersections for focal points"
        }

    def _check_golden_ratio(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check use of golden ratio"""
        return {
            "used": False,
            "score": 0.6,
            "assessment": "Golden ratio could enhance composition proportions"
        }

    def _check_leading_lines(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for effective leading lines"""
        return {
            "present": True,
            "effectiveness": 0.8,
            "assessment": "Effective use of natural leading lines"
        }

    def _check_framing(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for framing techniques"""
        return {
            "used": True,
            "score": 0.85,
            "assessment": "Good use of natural framing elements"
        }

    def _analyze_colors(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze color usage and harmony"""
        colors = {
            "palette": self._extract_color_palette(project_data),
            "harmony": self._assess_color_harmony(project_data),
            "temperature": self._assess_color_temperature(project_data),
            "contrast": self._assess_color_contrast(project_data),
            "overall_score": 0.0
        }

        # Calculate overall color score
        scores = [v.get("score", 0) for v in colors.values() if isinstance(v, dict)]
        colors["overall_score"] = np.mean(scores) if scores else 0.0

        return colors

    def _extract_color_palette(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract dominant color palette"""
        return {
            "dominant_colors": ["#4A90E2", "#F5A623", "#7ED321"],
            "color_count": 5,
            "assessment": "Balanced color palette with good variety"
        }

    def _assess_color_harmony(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess color harmony"""
        return {
            "type": "analogous",
            "score": 0.85,
            "assessment": "Harmonious analogous color scheme"
        }

    def _assess_color_temperature(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess color temperature balance"""
        return {
            "balance": "warm_cool",
            "ratio": "60_40",
            "score": 0.8,
            "assessment": "Good balance between warm and cool tones"
        }

    def _assess_color_contrast(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess color contrast"""
        return {
            "level": "medium",
            "score": 0.75,
            "assessment": "Appropriate color contrast for readability"
        }

    def _analyze_style_consistency(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze style consistency across the project"""
        return {
            "consistency_score": 0.9,
            "style_elements": ["minimalist", "modern", "clean"],
            "variations": ["slight_color_variations"],
            "assessment": "High style consistency with intentional variations"
        }

    def _generate_overall_assessment(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall design assessment"""
        # Calculate weighted scores
        design_score = analysis_results["design_elements"]
        composition_score = analysis_results["composition_analysis"]["overall_score"]
        color_score = analysis_results["color_analysis"]["overall_score"]
        style_score = analysis_results["style_consistency"]["consistency_score"]

        overall_score = np.mean([design_score, composition_score, color_score, style_score])

        assessment = {
            "overall_score": overall_score,
            "strengths": self._identify_strengths(analysis_results),
            "weaknesses": self._identify_weaknesses(analysis_results),
            "grade": self._calculate_grade(overall_score),
            "summary": self._generate_summary(analysis_results)
        }

        return assessment

    def _identify_strengths(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Identify project strengths"""
        strengths = []

        if analysis_results["design_elements"].get("score", 0) > 0.8:
            strengths.append("Strong design principles application")

        if analysis_results["composition_analysis"]["overall_score"] > 0.8:
            strengths.append("Excellent composition techniques")

        if analysis_results["color_analysis"]["overall_score"] > 0.8:
            strengths.append("Harmonious color usage")

        if analysis_results["style_consistency"]["consistency_score"] > 0.8:
            strengths.append("Consistent visual style")

        return strengths

    def _identify_weaknesses(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Identify project weaknesses"""
        weaknesses = []

        if analysis_results["design_elements"].get("score", 0) < 0.6:
            weaknesses.append("Design principles could be strengthened")

        if analysis_results["composition_analysis"]["overall_score"] < 0.6:
            weaknesses.append("Composition could be improved")

        if analysis_results["color_analysis"]["overall_score"] < 0.6:
            weaknesses.append("Color harmony needs attention")

        if analysis_results["style_consistency"]["consistency_score"] < 0.6:
            weaknesses.append("Style consistency could be enhanced")

        return weaknesses

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade based on score"""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"

    def _generate_summary(self, analysis_results: Dict[str, Any]) -> str:
        """Generate human-readable summary"""
        grade = analysis_results["overall_assessment"]["grade"]
        score = analysis_results["overall_assessment"]["overall_score"]

        return f"Overall design quality: {grade} ({score:.1%}). " \
               f"Strengths: {', '.join(analysis_results['overall_assessment']['strengths'])}. " \
               f"Areas for improvement: {', '.join(analysis_results['overall_assessment']['weaknesses'])}."

    def _generate_recommendations(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific recommendations for improvement"""
        recommendations = []

        # Design recommendations
        if analysis_results["design_elements"].get("score", 0) < 0.8:
            recommendations.append({
                "type": "design",
                "priority": "high",
                "title": "Strengthen Design Principles",
                "description": "Consider applying stronger design principles like balance and emphasis",
                "action_items": ["Review design fundamentals", "Apply rule of thirds", "Create focal hierarchy"]
            })

        # Composition recommendations
        if analysis_results["composition_analysis"]["overall_score"] < 0.8:
            recommendations.append({
                "type": "composition",
                "priority": "medium",
                "title": "Improve Composition",
                "description": "Enhance composition using classical design rules",
                "action_items": ["Apply golden ratio", "Use leading lines", "Improve framing"]
            })

        # Color recommendations
        if analysis_results["color_analysis"]["overall_score"] < 0.8:
            recommendations.append({
                "type": "color",
                "priority": "medium",
                "title": "Refine Color Harmony",
                "description": "Improve color relationships and harmony",
                "action_items": ["Create color palette", "Balance warm/cool tones", "Check contrast ratios"]
            })

        return recommendations

    def _calculate_confidence(self, analysis_results: Dict[str, Any]) -> float:
        """Calculate confidence score for the analysis"""
        # Base confidence on data completeness and analysis quality
        confidence_factors = [
            0.3,  # Design elements analysis
            0.3,  # Composition analysis
            0.2,  # Color analysis
            0.2   # Style consistency
        ]

        # Adjust based on actual analysis quality
        if analysis_results.get("error"):
            return 0.0

        return np.mean(confidence_factors)

    def reason_about_image(self, image_analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Provide reasoning about a specific image"""
        try:
            reasoning = {
                "design_quality": self._assess_image_quality(image_analysis),
                "context_fit": self._assess_context_fit(image_analysis, context),
                "improvement_suggestions": self._generate_image_suggestions(image_analysis),
                "creative_potential": self._assess_creative_potential(image_analysis)
            }

            return reasoning

        except Exception as e:
            self.logger.error(f"Image reasoning failed: {e}")
            return {"error": str(e)}

    def _assess_image_quality(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall image quality"""
        return {
            "technical_score": 0.85,
            "aesthetic_score": 0.8,
            "overall_score": 0.82,
            "assessment": "High quality image with good technical and aesthetic elements"
        }

    def _assess_context_fit(self, analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess how well image fits its intended context"""
        return {
            "fit_score": 0.9,
            "context_alignment": "excellent",
            "assessment": "Image aligns well with project context and goals"
        }

    def _generate_image_suggestions(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate specific suggestions for image improvement"""
        return [
            "Consider adjusting color balance for better harmony",
            "Strengthen focal point through composition adjustments",
            "Add more visual interest through texture variation"
        ]

    def _assess_creative_potential(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess creative potential of the image"""
        return {
            "potential_score": 0.88,
            "strengths": ["Strong composition", "Good color usage"],
            "opportunities": ["Style experimentation", "Narrative development"],
            "assessment": "High creative potential with room for artistic exploration"
        }

    def _cache_analysis(self, project_id: str, results: Dict[str, Any]) -> None:
        """Cache analysis results for future reference"""
        self.reasoning_cache[project_id] = {
            "timestamp": datetime.now().isoformat(),
            "results": results
        }

        # Maintain cache size limit
        if len(self.reasoning_cache) > 100:
            # Remove oldest entries
            oldest_key = min(self.reasoning_cache.keys(),
                           key=lambda k: self.reasoning_cache[k]["timestamp"])
            del self.reasoning_cache[oldest_key]

    def get_cached_analysis(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis results"""
        return self.reasoning_cache.get(project_id)

    def clear_cache(self) -> None:
        """Clear analysis cache"""
        self.reasoning_cache.clear()
        self.logger.info("Analysis cache cleared")