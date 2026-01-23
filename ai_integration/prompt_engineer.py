"""
Prompt Engineer
Handles prompt optimization, refinement, and generation for AI models
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

class PromptEngineer:
    """
    Engine for crafting, optimizing, and refining prompts for AI models
    """

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Prompt templates and patterns
        self.templates = {}
        self.prompt_history = []
        self.optimization_rules = {}

        # Performance tracking
        self.prompt_performance = {}

        # Initialize templates
        self._initialize_templates()

    def _initialize_templates(self):
        """Initialize prompt templates for different creative tasks"""
        self.templates = {
            "image_analysis": {
                "basic": "Analyze this image and describe its style, composition, colors, and mood: {image_description}",
                "detailed": "Provide a comprehensive analysis of this image including: visual style, color palette, composition techniques, lighting, mood, and artistic influences. Image: {image_description}",
                "creative": "Imagine you're an art critic. Describe this image with vivid, evocative language that captures its essence and artistic merit: {image_description}"
            },
            "style_suggestion": {
                "basic": "Suggest improvements for this creative work: {work_description}",
                "detailed": "As a creative director, analyze this work and provide specific suggestions for: composition improvements, color enhancements, style refinements, and technical adjustments. Work: {work_description}",
                "inspirational": "Channel your inner creative genius and suggest bold, innovative ways to elevate this work to the next level: {work_description}"
            },
            "workflow_optimization": {
                "basic": "Optimize this workflow: {workflow_description}",
                "detailed": "Analyze this creative workflow and suggest optimizations for: efficiency, quality improvement, resource usage, and creative output. Workflow: {workflow_description}",
                "strategic": "As a workflow architect, redesign this creative process for maximum efficiency and artistic impact: {workflow_description}"
            },
            "text_generation": {
                "basic": "Generate creative text for: {topic}",
                "detailed": "Create compelling, original content that captures the essence of: {topic}. Consider tone, style, and audience.",
                "poetic": "Craft poetic, evocative language that brings {topic} to life through metaphor and imagery."
            }
        }

        # Optimization rules
        self.optimization_rules = {
            "clarity": [
                "Use specific, concrete language",
                "Avoid ambiguous terms",
                "Provide clear context",
                "Specify desired output format"
            ],
            "specificity": [
                "Include specific details and examples",
                "Define scope and constraints",
                "Mention desired style or tone",
                "Specify length or complexity level"
            ],
            "creativity": [
                "Encourage innovative thinking",
                "Suggest multiple approaches",
                "Include inspirational elements",
                "Allow for creative interpretation"
            ],
            "efficiency": [
                "Break complex tasks into steps",
                "Provide clear success criteria",
                "Include time or resource constraints",
                "Specify priority levels"
            ]
        }

    def craft_prompt(self, task_type: str, context: Dict[str, Any],
                    template_level: str = "detailed") -> str:
        """
        Craft an optimized prompt for a specific task

        Args:
            task_type: Type of creative task
            context: Context information for the prompt
            template_level: Level of detail ('basic', 'detailed', 'creative')

        Returns:
            Optimized prompt string
        """
        try:
            if task_type not in self.templates:
                self.logger.warning(f"Unknown task type: {task_type}, using basic template")
                task_type = "text_generation"

            template = self.templates[task_type].get(template_level, self.templates[task_type]["basic"])

            # Fill in template variables
            prompt = self._fill_template_variables(template, context)

            # Apply optimization rules
            prompt = self._apply_optimization_rules(prompt, task_type)

            # Track prompt creation
            self._track_prompt(prompt, task_type, context)

            return prompt

        except Exception as e:
            self.logger.error(f"Failed to craft prompt: {e}")
            return f"Please analyze and provide creative input for: {context}"

    def _fill_template_variables(self, template: str, context: Dict[str, Any]) -> str:
        """Fill in template variables with context data"""
        prompt = template

        # Replace simple variables
        for key, value in context.items():
            if isinstance(value, str):
                prompt = prompt.replace(f"{{{key}}}", value)
            elif isinstance(value, (list, dict)):
                # Convert complex types to readable strings
                prompt = prompt.replace(f"{{{key}}}", str(value))

        # Handle unfilled variables
        prompt = re.sub(r'\{[^}]+\}', '[not specified]', prompt)

        return prompt

    def _apply_optimization_rules(self, prompt: str, task_type: str) -> str:
        """Apply optimization rules to improve prompt effectiveness"""
        optimized_prompt = prompt

        # Add task-specific optimizations
        if task_type in ["image_analysis", "style_suggestion"]:
            # Add visual analysis guidance
            if "analyze" in prompt.lower():
                optimized_prompt += "\n\nFocus on: composition, color theory, lighting, style consistency, and creative potential."

        elif task_type == "workflow_optimization":
            # Add workflow-specific guidance
            optimized_prompt += "\n\nConsider: step efficiency, resource utilization, quality control, and scalability."

        elif task_type == "text_generation":
            # Add creative writing guidance
            optimized_prompt += "\n\nEnsure the content is: original, engaging, well-structured, and aligned with the creative vision."

        return optimized_prompt

    def refine_prompt(self, original_prompt: str, feedback: Dict[str, Any]) -> str:
        """
        Refine a prompt based on feedback

        Args:
            original_prompt: The original prompt
            feedback: Feedback data with improvement suggestions

        Returns:
            Refined prompt
        """
        try:
            refined_prompt = original_prompt

            # Apply feedback-based improvements
            if feedback.get("too_vague"):
                refined_prompt = self._add_specificity(refined_prompt)

            if feedback.get("too_generic"):
                refined_prompt = self._add_creativity(refined_prompt)

            if feedback.get("missing_context"):
                refined_prompt = self._add_context(refined_prompt, feedback.get("context_hints", []))

            if feedback.get("improve_structure"):
                refined_prompt = self._improve_structure(refined_prompt)

            # Track refinement
            self._track_refinement(original_prompt, refined_prompt, feedback)

            return refined_prompt

        except Exception as e:
            self.logger.error(f"Failed to refine prompt: {e}")
            return original_prompt

    def _add_specificity(self, prompt: str) -> str:
        """Add specificity to a vague prompt"""
        specificity_additions = [
            " Be specific about the desired style, technique, or outcome.",
            " Include concrete examples or references.",
            " Specify the scope and constraints of the task."
        ]

        return prompt + specificity_additions[0]

    def _add_creativity(self, prompt: str) -> str:
        """Add creative elements to a generic prompt"""
        creativity_additions = [
            " Think creatively and suggest innovative approaches.",
            " Consider unconventional solutions or techniques.",
            " Explore multiple creative directions."
        ]

        return prompt + creativity_additions[0]

    def _add_context(self, prompt: str, context_hints: List[str]) -> str:
        """Add context information to a prompt"""
        if not context_hints:
            return prompt + " Provide additional context and background information."

        context_text = " Consider the following context: " + ", ".join(context_hints)
        return prompt + context_text

    def _improve_structure(self, prompt: str) -> str:
        """Improve the structure of a prompt"""
        return "Please provide a well-structured response to: " + prompt

    def generate_prompt_variations(self, base_prompt: str, num_variations: int = 3) -> List[str]:
        """
        Generate variations of a prompt for testing

        Args:
            base_prompt: Base prompt to vary
            num_variations: Number of variations to generate

        Returns:
            List of prompt variations
        """
        variations = [base_prompt]  # Include original

        try:
            # Generate variations by applying different optimization rules
            for i in range(num_variations - 1):
                variation = base_prompt

                # Apply random optimization strategies
                if i == 0:
                    variation = self._add_specificity(variation)
                elif i == 1:
                    variation = self._add_creativity(variation)
                elif i == 2:
                    variation = self._improve_structure(variation)

                variations.append(variation)

        except Exception as e:
            self.logger.error(f"Failed to generate prompt variations: {e}")

        return variations

    def evaluate_prompt_effectiveness(self, prompt: str, response_quality: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate how effective a prompt was based on response quality

        Args:
            prompt: The prompt used
            response_quality: Metrics about the response quality

        Returns:
            Effectiveness evaluation
        """
        evaluation = {
            "prompt_length": len(prompt),
            "clarity_score": 0,
            "specificity_score": 0,
            "creativity_score": 0,
            "overall_effectiveness": 0,
            "improvement_suggestions": []
        }

        try:
            # Analyze prompt characteristics
            evaluation["clarity_score"] = self._score_clarity(prompt)
            evaluation["specificity_score"] = self._score_specificity(prompt)
            evaluation["creativity_score"] = self._score_creativity(prompt)

            # Calculate overall effectiveness
            evaluation["overall_effectiveness"] = (
                evaluation["clarity_score"] +
                evaluation["specificity_score"] +
                evaluation["creativity_score"]
            ) / 3

            # Generate improvement suggestions
            evaluation["improvement_suggestions"] = self._generate_improvements(
                evaluation["clarity_score"],
                evaluation["specificity_score"],
                evaluation["creativity_score"]
            )

            # Track evaluation
            self._track_evaluation(prompt, evaluation, response_quality)

        except Exception as e:
            self.logger.error(f"Failed to evaluate prompt effectiveness: {e}")

        return evaluation

    def _score_clarity(self, prompt: str) -> float:
        """Score prompt clarity (0-1)"""
        score = 0.5  # Base score

        # Check for clear instructions
        if any(word in prompt.lower() for word in ["analyze", "describe", "create", "suggest"]):
            score += 0.2

        # Check for specific details
        if len(prompt.split()) > 10:
            score += 0.1

        # Check for structure
        if ":" in prompt or "\n" in prompt:
            score += 0.2

        return min(1.0, score)

    def _score_specificity(self, prompt: str) -> float:
        """Score prompt specificity (0-1)"""
        score = 0.3  # Base score

        # Check for specific terms
        specific_indicators = ["specific", "detailed", "exact", "particular", "style:", "technique:"]
        if any(indicator in prompt.lower() for indicator in specific_indicators):
            score += 0.3

        # Check for examples or references
        if any(word in prompt.lower() for word in ["example", "reference", "like", "similar to"]):
            score += 0.2

        # Check for constraints
        if any(word in prompt.lower() for word in ["must", "should", "limit", "constraint"]):
            score += 0.2

        return min(1.0, score)

    def _score_creativity(self, prompt: str) -> float:
        """Score prompt creativity encouragement (0-1)"""
        score = 0.4  # Base score

        # Check for creative language
        creative_indicators = ["creative", "innovative", "imagine", "explore", "bold", "unique"]
        if any(indicator in prompt.lower() for indicator in creative_indicators):
            score += 0.3

        # Check for open-ended questions
        if "?" in prompt:
            score += 0.1

        # Check for multiple options
        if any(word in prompt.lower() for word in ["options", "alternatives", "variations"]):
            score += 0.2

        return min(1.0, score)

    def _generate_improvements(self, clarity: float, specificity: float, creativity: float) -> List[str]:
        """Generate improvement suggestions based on scores"""
        suggestions = []

        if clarity < 0.6:
            suggestions.append("Add clearer instructions and structure to the prompt")

        if specificity < 0.6:
            suggestions.append("Include more specific details, examples, and constraints")

        if creativity < 0.6:
            suggestions.append("Encourage more creative thinking and exploration")

        if not suggestions:
            suggestions.append("Prompt is well-balanced across clarity, specificity, and creativity")

        return suggestions

    def _track_prompt(self, prompt: str, task_type: str, context: Dict[str, Any]):
        """Track prompt creation for analytics"""
        self.prompt_history.append({
            "prompt": prompt,
            "task_type": task_type,
            "context": context,
            "created_at": datetime.now(),
            "version": "crafted"
        })

    def _track_refinement(self, original: str, refined: str, feedback: Dict[str, Any]):
        """Track prompt refinement"""
        self.prompt_history.append({
            "original_prompt": original,
            "refined_prompt": refined,
            "feedback": feedback,
            "created_at": datetime.now(),
            "version": "refined"
        })

    def _track_evaluation(self, prompt: str, evaluation: Dict[str, Any], response_quality: Dict[str, Any]):
        """Track prompt evaluation"""
        prompt_key = hash(prompt)  # Simple hash for tracking
        self.prompt_performance[prompt_key] = {
            "prompt": prompt,
            "evaluation": evaluation,
            "response_quality": response_quality,
            "evaluated_at": datetime.now()
        }

    def get_prompt_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent prompt history"""
        return self.prompt_history[-limit:]

    def get_prompt_analytics(self) -> Dict[str, Any]:
        """Get analytics about prompt performance"""
        if not self.prompt_performance:
            return {"total_evaluations": 0}

        evaluations = list(self.prompt_performance.values())

        return {
            "total_evaluations": len(evaluations),
            "avg_effectiveness": sum(e["evaluation"]["overall_effectiveness"] for e in evaluations) / len(evaluations),
            "avg_clarity": sum(e["evaluation"]["clarity_score"] for e in evaluations) / len(evaluations),
            "avg_specificity": sum(e["evaluation"]["specificity_score"] for e in evaluations) / len(evaluations),
            "avg_creativity": sum(e["evaluation"]["creativity_score"] for e in evaluations) / len(evaluations)
        }

    def save_prompt_data(self, filepath: str) -> bool:
        """Save prompt data to file"""
        try:
            data = {
                "prompt_history": self.prompt_history,
                "prompt_performance": self.prompt_performance,
                "templates": self.templates,
                "export_timestamp": datetime.now().isoformat()
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            return True

        except Exception as e:
            self.logger.error(f"Failed to save prompt data: {e}")
            return False

    def load_prompt_data(self, filepath: str) -> bool:
        """Load prompt data from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.prompt_history = data.get("prompt_history", [])
            self.prompt_performance = data.get("prompt_performance", {})
            self.templates = data.get("templates", {})

            return True

        except Exception as e:
            self.logger.error(f"Failed to load prompt data: {e}")
            return False