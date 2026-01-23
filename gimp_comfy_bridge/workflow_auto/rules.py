"""
Rule Engine for workflow auto-generation.

This module provides rule-based selection and modification logic for
automatically assembling ComfyUI workflows based on templates and styles.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import json

from ..shared.config import Config
from ..shared.types import Style, WorkflowTemplate

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    """Represents a workflow generation rule."""
    id: str
    name: str
    description: str
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleContext:
    """Context for rule evaluation."""
    template: WorkflowTemplate
    style: Optional[Style] = None
    user_options: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleResult:
    """Result of rule evaluation."""
    rule_id: str
    matched: bool
    actions: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowRules:
    """
    Collection of workflow generation rules.

    This class manages a set of rules for workflow assembly and provides
    methods for loading, saving, and querying rules.
    """

    def __init__(self, config: Config):
        """
        Initialize workflow rules.

        Args:
            config: Application configuration
        """
        self.config = config
        self.rules: Dict[str, Rule] = {}
        self._load_default_rules()

    def _load_default_rules(self):
        """Load default workflow generation rules."""
        default_rules = [
            Rule(
                id="basic_txt2img",
                name="Basic Text-to-Image",
                description="Basic text-to-image generation workflow",
                conditions=[
                    {"type": "template_type", "value": "txt2img"},
                    {"type": "style_category", "value": "basic"}
                ],
                actions=[
                    {
                        "type": "add_node",
                        "node_type": "CLIPTextEncode",
                        "properties": {"text": "{prompt}"}
                    },
                    {
                        "type": "add_node",
                        "node_type": "KSampler",
                        "properties": {
                            "seed": "{seed}",
                            "steps": 20,
                            "cfg": 7.0,
                            "sampler_name": "euler",
                            "scheduler": "normal"
                        }
                    },
                    {
                        "type": "add_connection",
                        "source": "CLIPTextEncode",
                        "target": "KSampler",
                        "source_output": 0,
                        "target_input": 0
                    }
                ]
            ),
            Rule(
                id="style_lora_integration",
                name="LoRA Style Integration",
                description="Integrate LoRA models for style application",
                conditions=[
                    {"type": "has_style", "value": True},
                    {"type": "style_has_loras", "value": True}
                ],
                actions=[
                    {
                        "type": "add_node",
                        "node_type": "LoraLoader",
                        "properties": {"lora_name": "{style.loras[0]}"}
                    },
                    {
                        "type": "modify_node",
                        "node_id": "CLIPTextEncode",
                        "properties": {"text": "{prompt} <lora:{style.loras[0]}:1.0>"}
                    }
                ]
            ),
            Rule(
                id="high_quality_upscaling",
                name="High Quality Upscaling",
                description="Add upscaling nodes for high quality output",
                conditions=[
                    {"type": "quality_level", "value": "high"},
                    {"type": "output_resolution", "operator": ">", "value": 1024}
                ],
                actions=[
                    {
                        "type": "add_node",
                        "node_type": "UpscaleModelLoader",
                        "properties": {"model_name": "4x-UltraSharp.pth"}
                    },
                    {
                        "type": "add_node",
                        "node_type": "ImageUpscaleWithModel",
                        "properties": {}
                    }
                ]
            ),
            Rule(
                id="batch_processing",
                name="Batch Processing",
                description="Enable batch processing for multiple generations",
                conditions=[
                    {"type": "batch_size", "operator": ">", "value": 1}
                ],
                actions=[
                    {
                        "type": "modify_node",
                        "node_id": "KSampler",
                        "properties": {"batch_size": "{batch_size}"}
                    }
                ]
            )
        ]

        for rule in default_rules:
            self.rules[rule.id] = rule

    def add_rule(self, rule: Rule) -> None:
        """
        Add a new rule.

        Args:
            rule: Rule to add
        """
        self.rules[rule.id] = rule
        logger.info(f"Added rule: {rule.id}")

    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a rule.

        Args:
            rule_id: ID of rule to remove

        Returns:
            True if rule was removed
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed rule: {rule_id}")
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """
        Get a rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Rule if found, None otherwise
        """
        return self.rules.get(rule_id)

    def list_rules(self, enabled_only: bool = False) -> List[Rule]:
        """
        List all rules.

        Args:
            enabled_only: Only return enabled rules

        Returns:
            List of rules
        """
        rules = list(self.rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return sorted(rules, key=lambda r: r.priority, reverse=True)

    def save_rules(self, filepath: Optional[Path] = None) -> None:
        """
        Save rules to file.

        Args:
            filepath: File path to save to
        """
        if filepath is None:
            filepath = self.config.data_dir / "workflow_rules.json"

        rules_data = {
            "version": "1.0",
            "rules": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "conditions": rule.conditions,
                    "actions": rule.actions,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "metadata": rule.metadata
                }
                for rule in self.rules.values()
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(rules_data, f, indent=2)

        logger.info(f"Saved {len(self.rules)} rules to {filepath}")

    def load_rules(self, filepath: Optional[Path] = None) -> None:
        """
        Load rules from file.

        Args:
            filepath: File path to load from
        """
        if filepath is None:
            filepath = self.config.data_dir / "workflow_rules.json"

        if not filepath.exists():
            logger.info(f"Rules file not found: {filepath}")
            return

        with open(filepath, 'r') as f:
            data = json.load(f)

        loaded_count = 0
        for rule_data in data.get("rules", []):
            rule = Rule(
                id=rule_data["id"],
                name=rule_data["name"],
                description=rule_data["description"],
                conditions=rule_data["conditions"],
                actions=rule_data["actions"],
                priority=rule_data.get("priority", 0),
                enabled=rule_data.get("enabled", True),
                metadata=rule_data.get("metadata", {})
            )
            self.rules[rule.id] = rule
            loaded_count += 1

        logger.info(f"Loaded {loaded_count} rules from {filepath}")


class RuleEngine:
    """
    Rule engine for workflow auto-generation.

    This class evaluates rules against context and generates appropriate
    modifications for workflow assembly.
    """

    def __init__(self, config: Config):
        """
        Initialize rule engine.

        Args:
            config: Application configuration
        """
        self.config = config
        self.rules = WorkflowRules(config)

    async def evaluate_rules(self, context: RuleContext) -> List[RuleResult]:
        """
        Evaluate all rules against the given context.

        Args:
            context: Rule evaluation context

        Returns:
            List of rule evaluation results
        """
        results = []

        for rule in self.rules.list_rules(enabled_only=True):
            result = await self._evaluate_rule(rule, context)
            if result.matched:
                results.append(result)

        # Sort by confidence and priority
        results.sort(key=lambda r: (r.confidence, r.metadata.get("priority", 0)), reverse=True)

        return results

    async def _evaluate_rule(self, rule: Rule, context: RuleContext) -> RuleResult:
        """
        Evaluate a single rule against context.

        Args:
            rule: Rule to evaluate
            context: Evaluation context

        Returns:
            Rule evaluation result
        """
        matched_conditions = 0
        total_conditions = len(rule.conditions)

        for condition in rule.conditions:
            if await self._check_condition(condition, context):
                matched_conditions += 1

        # Rule matches if all conditions are met
        matched = matched_conditions == total_conditions
        confidence = matched_conditions / total_conditions if total_conditions > 0 else 0

        return RuleResult(
            rule_id=rule.id,
            matched=matched,
            actions=rule.actions if matched else [],
            confidence=confidence,
            metadata={"priority": rule.priority}
        )

    async def _check_condition(self, condition: Dict[str, Any], context: RuleContext) -> bool:
        """
        Check if a condition matches the context.

        Args:
            condition: Condition to check
            context: Evaluation context

        Returns:
            True if condition matches
        """
        cond_type = condition.get("type")
        value = condition.get("value")
        operator = condition.get("operator", "==")

        if cond_type == "template_type":
            return context.template.type == value

        elif cond_type == "style_category":
            return context.style and context.style.category == value

        elif cond_type == "has_style":
            return (context.style is not None) == value

        elif cond_type == "style_has_loras":
            return context.style and bool(context.style.loras)

        elif cond_type == "quality_level":
            return context.user_options.get("quality", "normal") == value

        elif cond_type == "output_resolution":
            resolution = context.user_options.get("resolution", 512)
            if operator == ">":
                return resolution > value
            elif operator == "<":
                return resolution < value
            elif operator == ">=":
                return resolution >= value
            elif operator == "<=":
                return resolution <= value
            else:
                return resolution == value

        elif cond_type == "batch_size":
            batch_size = context.user_options.get("batch_size", 1)
            if operator == ">":
                return batch_size > value
            elif operator == "<":
                return batch_size < value
            elif operator == ">=":
                return batch_size >= value
            elif operator == "<=":
                return batch_size <= value
            else:
                return batch_size == value

        # Default: check user options
        actual_value = context.user_options.get(cond_type)
        if operator == "==":
            return actual_value == value
        elif operator == "!=":
            return actual_value != value
        elif operator == ">":
            return actual_value > value if actual_value is not None else False
        elif operator == "<":
            return actual_value < value if actual_value is not None else False
        elif operator == ">=":
            return actual_value >= value if actual_value is not None else False
        elif operator == "<=":
            return actual_value <= value if actual_value is not None else False

        return False

    async def get_style_modifications(self, style: Style) -> List[Dict[str, Any]]:
        """
        Get workflow modifications for a style.

        Args:
            style: Style to get modifications for

        Returns:
            List of modification actions
        """
        modifications = []

        # Add LoRA loading nodes
        for i, lora in enumerate(style.loras):
            modifications.append({
                "type": "add_node",
                "node_id": f"lora_loader_{i}",
                "node_type": "LoraLoader",
                "properties": {
                    "lora_name": lora.name,
                    "strength_model": lora.strength,
                    "strength_clip": lora.strength
                },
                "position": {"x": 100 + i * 200, "y": 100}
            })

        # Modify prompt with LoRA triggers
        if style.loras:
            lora_triggers = [f"<lora:{lora.name}:{lora.strength}>" for lora in style.loras]
            modifications.append({
                "type": "modify_node",
                "node_id": "CLIPTextEncode",
                "properties": {
                    "text": "{prompt} " + " ".join(lora_triggers)
                }
            })

        # Apply style-specific sampler settings
        if hasattr(style, 'sampler_settings'):
            modifications.append({
                "type": "modify_node",
                "node_id": "KSampler",
                "properties": style.sampler_settings
            })

        return modifications

    async def get_template_modifications(self, template: WorkflowTemplate) -> List[Dict[str, Any]]:
        """
        Get workflow modifications for a template.

        Args:
            template: Template to get modifications for

        Returns:
            List of modification actions
        """
        modifications = []

        # Template-specific modifications would go here
        # This is a placeholder for template-specific logic

        return modifications

    def create_context(
        self,
        template: WorkflowTemplate,
        style: Optional[Style] = None,
        user_options: Optional[Dict[str, Any]] = None
    ) -> RuleContext:
        """
        Create a rule evaluation context.

        Args:
            template: Workflow template
            style: Optional style
            user_options: User-provided options

        Returns:
            RuleContext for evaluation
        """
        if user_options is None:
            user_options = {}

        return RuleContext(
            template=template,
            style=style,
            user_options=user_options,
            environment={
                "available_models": [],  # Would be populated from model registry
                "available_loras": [],   # Would be populated from LoRA registry
                "system_capabilities": {}  # System capabilities
            }
        )