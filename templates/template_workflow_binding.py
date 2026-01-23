#!/usr/bin/env python3
"""
Template-Workflow Binding System for Comfy Gimpy Studio

Manages the connection between templates and ComfyUI workflows.
Handles parameter mapping, workflow execution, and result processing.
"""

import json
import pathlib
import requests
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import time
import uuid
import sys


@dataclass
class WorkflowParameter:
    """Represents a parameter in a ComfyUI workflow."""
    name: str
    param_type: str
    default_value: Any
    description: str = ""


@dataclass
class WorkflowBinding:
    """Represents the binding between a template and a workflow."""
    template_id: str
    workflow_name: str
    parameter_mappings: Dict[str, str]  # template_param -> workflow_param
    workflow_parameters: Dict[str, WorkflowParameter]
    output_mappings: Dict[str, str]  # workflow_output -> template_layer


class WorkflowBinder:
    """Manages template-to-workflow bindings and execution."""

    def __init__(self, comfyui_url: str = "http://127.0.0.1:8188"):
        """
        Initialize the workflow binder.

        Args:
            comfyui_url: URL of the ComfyUI server
        """
        self.comfyui_url = comfyui_url.rstrip('/')
        self._workflow_cache: Dict[str, Dict] = {}
        self._binding_cache: Dict[str, WorkflowBinding] = {}

    def load_workflow(self, workflow_name: str) -> Optional[Dict]:
        """
        Load a workflow definition from ComfyUI.

        Args:
            workflow_name: Name of the workflow to load

        Returns:
            Workflow definition dictionary or None if not found
        """
        if workflow_name in self._workflow_cache:
            return self._workflow_cache[workflow_name]

        try:
            # In a real implementation, this would query ComfyUI for available workflows
            # For now, we'll create a mock workflow structure
            workflow = self._create_mock_workflow(workflow_name)
            self._workflow_cache[workflow_name] = workflow
            return workflow

        except Exception as e:
            print(f"Failed to load workflow {workflow_name}: {e}")
            return None

    def _create_mock_workflow(self, workflow_name: str) -> Dict:
        """Create a mock workflow definition for testing."""
        # This is a simplified mock - in reality, workflows would be loaded from ComfyUI
        return {
            "name": workflow_name,
            "nodes": {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {"image": "input_image.png"}
                },
                "2": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": "prompt_text", "clip": ["CLIPLoader", 0]}
                },
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "model": ["CheckpointLoaderSimple", 0],
                        "positive": ["CLIPTextEncode", 0],
                        "negative": ["CLIPTextEncode", 1],
                        "latent_image": ["EmptyLatentImage", 0]
                    }
                }
            },
            "parameters": {
                "prompt_text": WorkflowParameter("prompt_text", "string", "A beautiful image", "Text prompt for generation"),
                "input_image": WorkflowParameter("input_image", "image", None, "Input image file"),
                "width": WorkflowParameter("width", "integer", 512, "Output width"),
                "height": WorkflowParameter("height", "integer", 512, "Output height")
            }
        }

    def create_binding(self, template_data: Dict, template_id: str) -> WorkflowBinding:
        """
        Create a binding between a template and its workflow.

        Args:
            template_data: Template metadata dictionary
            template_id: Template identifier

        Returns:
            WorkflowBinding object
        """
        workflow_bindings = template_data.get('workflow_bindings', {})
        workflow_name = workflow_bindings.get('default_workflow', 'default_workflow')
        parameter_mappings = workflow_bindings.get('parameter_mappings', {})

        # Load workflow to get parameter definitions
        workflow = self.load_workflow(workflow_name)
        workflow_params = {}
        if workflow and 'parameters' in workflow:
            workflow_params = workflow['parameters']

        # Create output mappings (simplified - would map workflow outputs to template layers)
        output_mappings = {
            "generated_image": "hero_image"  # Example mapping
        }

        binding = WorkflowBinding(
            template_id=template_id,
            workflow_name=workflow_name,
            parameter_mappings=parameter_mappings,
            workflow_parameters=workflow_params,
            output_mappings=output_mappings
        )

        self._binding_cache[template_id] = binding
        return binding

    def prepare_workflow_execution(self, binding: WorkflowBinding,
                                 template_parameters: Dict[str, Any]) -> Tuple[bool, Dict]:
        """
        Prepare a workflow for execution with template parameters.

        Args:
            binding: Workflow binding
            template_parameters: User-provided template parameters

        Returns:
            Tuple of (success, workflow_execution_data)
        """
        try:
            # Load the base workflow
            workflow = self.load_workflow(binding.workflow_name)
            if not workflow:
                return False, {"error": f"Workflow {binding.workflow_name} not found"}

            # Create execution data by mapping template parameters to workflow parameters
            execution_data = {
                "workflow": workflow.copy(),
                "mapped_parameters": {},
                "execution_id": str(uuid.uuid4())
            }

            # Map template parameters to workflow parameters
            for template_param, workflow_param in binding.parameter_mappings.items():
                if template_param in template_parameters:
                    value = template_parameters[template_param]
                    execution_data["mapped_parameters"][workflow_param] = value

                    # Update the workflow with the mapped value
                    # This is simplified - real implementation would traverse workflow nodes
                    if workflow_param in execution_data["workflow"].get("parameters", {}):
                        execution_data["workflow"]["parameters"][workflow_param] = value

            return True, execution_data

        except Exception as e:
            return False, {"error": f"Failed to prepare workflow execution: {e}"}

    def execute_workflow(self, execution_data: Dict, timeout: int = 300) -> Tuple[bool, Dict]:
        """
        Execute a workflow on ComfyUI.

        Args:
            execution_data: Prepared execution data
            timeout: Execution timeout in seconds

        Returns:
            Tuple of (success, results)
        """
        try:
            workflow = execution_data["workflow"]
            execution_id = execution_data["execution_id"]

            # Send workflow to ComfyUI
            prompt_endpoint = f"{self.comfyui_url}/prompt"
            response = requests.post(prompt_endpoint, json={
                "prompt": workflow,
                "client_id": execution_id
            }, timeout=10)

            if response.status_code != 200:
                return False, {"error": f"Failed to queue workflow: {response.text}"}

            prompt_id = response.json().get("prompt_id")

            # Poll for completion
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Check execution status
                history_endpoint = f"{self.comfyui_url}/history/{prompt_id}"
                history_response = requests.get(history_endpoint, timeout=5)

                if history_response.status_code == 200:
                    history = history_response.json()
                    if prompt_id in history:
                        status = history[prompt_id].get("status", {})
                        if status.get("completed"):
                            # Execution completed
                            outputs = history[prompt_id].get("outputs", {})
                            return True, {
                                "execution_id": execution_id,
                                "prompt_id": prompt_id,
                                "outputs": outputs
                            }
                        elif status.get("exception"):
                            # Execution failed
                            return False, {
                                "error": f"Workflow execution failed: {status.get('exception')}",
                                "execution_id": execution_id
                            }

                time.sleep(1)  # Wait before polling again

            return False, {"error": "Workflow execution timed out", "execution_id": execution_id}

        except requests.RequestException as e:
            return False, {"error": f"Network error during workflow execution: {e}"}
        except Exception as e:
            return False, {"error": f"Unexpected error during workflow execution: {e}"}

    def process_execution_results(self, binding: WorkflowBinding, results: Dict) -> Dict[str, Any]:
        """
        Process workflow execution results for template integration.

        Args:
            binding: Workflow binding
            results: Execution results from ComfyUI

        Returns:
            Processed results mapped to template layers
        """
        processed_results = {
            "execution_id": results.get("execution_id"),
            "timestamp": time.time(),
            "layer_updates": {}
        }

        # Map workflow outputs to template layers
        outputs = results.get("outputs", {})
        for workflow_output, template_layer in binding.output_mappings.items():
            if workflow_output in outputs:
                processed_results["layer_updates"][template_layer] = {
                    "data": outputs[workflow_output],
                    "source": "workflow_generation"
                }

        return processed_results

    def validate_parameter_compatibility(self, binding: WorkflowBinding,
                                       template_parameters: Dict[str, Any]) -> List[str]:
        """
        Validate that provided template parameters are compatible with the workflow.

        Args:
            binding: Workflow binding
            template_parameters: Parameters to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Check required parameters
        for template_param, workflow_param in binding.parameter_mappings.items():
            if template_param not in template_parameters:
                # Check if workflow parameter has a default
                workflow_param_def = binding.workflow_parameters.get(workflow_param)
                if workflow_param_def and workflow_param_def.default_value is None:
                    errors.append(f"Required parameter '{template_param}' is missing")

        # Check parameter types (simplified validation)
        for template_param, value in template_parameters.items():
            if template_param in binding.parameter_mappings:
                workflow_param = binding.parameter_mappings[template_param]
                workflow_param_def = binding.workflow_parameters.get(workflow_param)

                if workflow_param_def:
                    expected_type = workflow_param_def.param_type
                    if expected_type == "integer" and not isinstance(value, int):
                        errors.append(f"Parameter '{template_param}' should be an integer")
                    elif expected_type == "string" and not isinstance(value, str):
                        errors.append(f"Parameter '{template_param}' should be a string")

        return errors


class TemplateWorkflowManager:
    """High-level manager for template-workflow operations."""

    def __init__(self, templates_dir: pathlib.Path, comfyui_url: str = "http://127.0.0.1:8188"):
        """
        Initialize the template-workflow manager.

        Args:
            templates_dir: Directory containing templates
            comfyui_url: ComfyUI server URL
        """
        self.templates_dir = templates_dir
        self.workflow_binder = WorkflowBinder(comfyui_url)
        self._bindings_cache: Dict[str, WorkflowBinding] = {}

    def execute_template_workflow(self, template_id: str,
                                template_parameters: Dict[str, Any]) -> Tuple[bool, Dict]:
        """
        Execute a template's workflow with given parameters.

        Args:
            template_id: Template identifier
            template_parameters: User parameters for the template

        Returns:
            Tuple of (success, results)
        """
        try:
            # Load template
            template_path = self._get_template_path(template_id)
            if not template_path.exists():
                return False, {"error": f"Template not found: {template_id}"}

            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            # Get or create binding
            if template_id not in self._bindings_cache:
                binding = self.workflow_binder.create_binding(template_data, template_id)
                self._bindings_cache[template_id] = binding
            else:
                binding = self._bindings_cache[template_id]

            # Validate parameters
            validation_errors = self.workflow_binder.validate_parameter_compatibility(
                binding, template_parameters)
            if validation_errors:
                return False, {"error": "Parameter validation failed", "details": validation_errors}

            # Prepare execution
            success, execution_data = self.workflow_binder.prepare_workflow_execution(
                binding, template_parameters)
            if not success:
                return False, execution_data

            # Execute workflow
            success, results = self.workflow_binder.execute_workflow(execution_data)
            if not success:
                return False, results

            # Process results
            processed_results = self.workflow_binder.process_execution_results(binding, results)

            return True, processed_results

        except Exception as e:
            return False, {"error": f"Template workflow execution failed: {e}"}

    def _get_template_path(self, template_id: str) -> pathlib.Path:
        """Get the file path for a template."""
        category, template_name = template_id.split('/', 1)
        return self.templates_dir / category / f"{template_name}.json"

    def get_workflow_requirements(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow requirements for a template.

        Args:
            template_id: Template identifier

        Returns:
            Dictionary of workflow requirements or None if not found
        """
        try:
            template_path = self._get_template_path(template_id)
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            workflow_bindings = template_data.get('workflow_bindings', {})
            return {
                "workflow_name": workflow_bindings.get('default_workflow'),
                "alternative_workflows": workflow_bindings.get('alternative_workflows', []),
                "parameter_mappings": workflow_bindings.get('parameter_mappings', {})
            }
        except:
            return None


def main():
    """Command-line interface for workflow binding operations."""
    if len(sys.argv) < 3:
        print("Usage: python template_workflow_binding.py <templates_dir> <command> [args...]")
        print("Commands:")
        print("  requirements <template_id>    - Show workflow requirements")
        print("  validate <template_id> <params_json> - Validate parameters")
        sys.exit(1)

    templates_dir = pathlib.Path(sys.argv[1])
    command = sys.argv[2]

    manager = TemplateWorkflowManager(templates_dir)

    if command == 'requirements' and len(sys.argv) > 3:
        template_id = sys.argv[3]
        requirements = manager.get_workflow_requirements(template_id)

        if requirements:
            print(f"Workflow requirements for {template_id}:")
            print(f"  Primary workflow: {requirements['workflow_name']}")
            print(f"  Alternatives: {', '.join(requirements['alternative_workflows'])}")
            print("  Parameter mappings:")
            for template_param, workflow_param in requirements['parameter_mappings'].items():
                print(f"    {template_param} -> {workflow_param}")
        else:
            print(f"Could not load requirements for {template_id}")

    elif command == 'validate' and len(sys.argv) > 4:
        template_id = sys.argv[3]
        params_json = sys.argv[4]

        try:
            template_parameters = json.loads(params_json)
            # For validation, we'd need to load the binding first
            print(f"Parameter validation for {template_id} would check: {template_parameters}")
            print("Note: Full validation requires binding creation")
        except json.JSONDecodeError:
            print("Invalid JSON in parameters")

    else:
        print("Invalid command or arguments")


if __name__ == '__main__':
    main()