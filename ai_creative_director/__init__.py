"""
AI Creative Director - Main Coordinator
Provides intelligent creative guidance and global design reasoning for Comfy Gimpy Studio
"""

import threading
import time
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from .reasoning_engine import DesignReasoningEngine
from .creative_assistant import CreativeAssistant
from .style_analyzer import StyleAnalyzer
from .workflow_optimizer import WorkflowOptimizer
from .session_manager import CollaborativeSessionManager
from .feedback_integrator import FeedbackIntegrator

# Import AI integration components
try:
    from ..ai_integration import ModelManager, PromptEngineer, ContextAnalyzer, CreativeMemory
except ImportError:
    ModelManager = PromptEngineer = ContextAnalyzer = CreativeMemory = None

# Import sync manager for integration
try:
    from ..sync_manager import SyncManager
except ImportError:
    SyncManager = None

class AICreativeDirector:
    """
    Main AI Creative Director class that coordinates all AI-powered creative features
    """

    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), '..', 'ai_config.json')
        self.config = self._load_config()

        # Core AI components
        self.reasoning_engine = None
        self.creative_assistant = None
        self.style_analyzer = None
        self.workflow_optimizer = None
        self.session_manager = None
        self.feedback_integrator = None

        # AI Integration components
        self.model_manager = None
        self.prompt_engineer = None
        self.context_analyzer = None
        self.creative_memory = None

        # Integration components
        self.sync_manager = SyncManager() if SyncManager else None

        # State management
        self.is_initialized = False
        self.active_sessions = {}
        self.creative_memory = {}
        self.performance_metrics = {}

        # Threading
        self.analysis_thread = None
        self.optimization_thread = None
        self.running = False

        self._initialize_components()

    def _load_config(self) -> Dict[str, Any]:
        """Load AI configuration from file"""
        default_config = {
            "enabled_features": {
                "design_reasoning": True,
                "creative_assistance": True,
                "style_analysis": True,
                "workflow_optimization": True,
                "collaborative_sessions": True,
                "feedback_learning": True
            },
            "ai_models": {
                "vision_model": "clip-vit-base-patch32",
                "language_model": "microsoft/DialoGPT-medium",
                "style_model": "openai/clip-vit-large-patch14",
                "local_processing": True,
                "cloud_fallback": False
            },
            "performance": {
                "max_concurrent_sessions": 5,
                "analysis_timeout": 30,
                "optimization_interval": 60,
                "memory_limit_mb": 1024
            },
            "collaboration": {
                "session_timeout": 3600,
                "max_participants": 10,
                "auto_save_interval": 300
            },
            "privacy": {
                "local_only": True,
                "data_retention_days": 30,
                "anonymous_feedback": True
            }
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                # Merge user config with defaults
                self._merge_config(default_config, user_config)
                return default_config
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")

        return default_config

    def _merge_config(self, base: Dict, update: Dict) -> None:
        """Recursively merge configuration dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _initialize_components(self) -> None:
        """Initialize all AI creative director components"""
        try:
            # Initialize core components based on config
            if self.config["enabled_features"]["design_reasoning"]:
                self.reasoning_engine = DesignReasoningEngine(self.config)

            if self.config["enabled_features"]["creative_assistance"]:
                self.creative_assistant = CreativeAssistant(self.config)

            if self.config["enabled_features"]["style_analysis"]:
                self.style_analyzer = StyleAnalyzer(self.config)

            if self.config["enabled_features"]["workflow_optimization"]:
                self.workflow_optimizer = WorkflowOptimizer(self.config)

            if self.config["enabled_features"]["collaborative_sessions"]:
                self.session_manager = CollaborativeSessionManager(self.config)

            if self.config["enabled_features"]["feedback_learning"]:
                self.feedback_integrator = FeedbackIntegrator(self.config)

            # Initialize AI integration components
            if ModelManager:
                self.model_manager = ModelManager(self.config)
            if PromptEngineer:
                self.prompt_engineer = PromptEngineer(self.config)
            if ContextAnalyzer:
                self.context_analyzer = ContextAnalyzer(self.config)
            if CreativeMemory:
                self.creative_memory = CreativeMemory(self.config)

            self.is_initialized = True
            self.logger.info("AI Creative Director components initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize AI components: {e}")
            self.is_initialized = False

    def start(self) -> bool:
        """Start the AI Creative Director system"""
        if not self.is_initialized:
            self.logger.error("Cannot start AI Creative Director - components not initialized")
            return False

        self.running = True

        # Start background analysis thread
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()

        # Start optimization thread
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()

        self.logger.info("AI Creative Director started successfully")
        return True

    def stop(self) -> None:
        """Stop the AI Creative Director system"""
        self.running = False

        # Wait for threads to finish
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=5)

        if self.optimization_thread and self.optimization_thread.is_alive():
            self.optimization_thread.join(timeout=5)

        # Save creative memory
        self._save_creative_memory()

        self.logger.info("AI Creative Director stopped")

    def _analysis_loop(self) -> None:
        """Background analysis loop for continuous creative monitoring"""
        while self.running:
            try:
                self._perform_continuous_analysis()
                time.sleep(self.config["performance"]["analysis_timeout"])
            except Exception as e:
                self.logger.error(f"Analysis loop error: {e}")
                time.sleep(5)

    def _optimization_loop(self) -> None:
        """Background optimization loop for workflow improvements"""
        while self.running:
            try:
                self._perform_workflow_optimization()
                time.sleep(self.config["performance"]["optimization_interval"])
            except Exception as e:
                self.logger.error(f"Optimization loop error: {e}")
                time.sleep(10)

    def _perform_continuous_analysis(self) -> None:
        """Perform continuous creative analysis"""
        if not self.reasoning_engine:
            return

        # Analyze active projects and workflows
        active_projects = self._get_active_projects()

        for project_id, project_data in active_projects.items():
            try:
                # Global design reasoning
                reasoning_results = self.reasoning_engine.analyze_project(project_data)

                # Style consistency analysis
                if self.style_analyzer:
                    style_results = self.style_analyzer.analyze_project_consistency(project_data)
                    reasoning_results.update(style_results)

                # Store analysis results
                self._store_analysis_results(project_id, reasoning_results)

                # Generate creative suggestions
                if self.creative_assistant:
                    suggestions = self.creative_assistant.generate_suggestions(reasoning_results)
                    self._broadcast_suggestions(project_id, suggestions)

            except Exception as e:
                self.logger.error(f"Analysis failed for project {project_id}: {e}")

    def _perform_workflow_optimization(self) -> None:
        """Perform workflow optimization analysis"""
        if not self.workflow_optimizer:
            return

        active_workflows = self._get_active_workflows()

        for workflow_id, workflow_data in active_workflows.items():
            try:
                # Analyze workflow efficiency
                optimization_results = self.workflow_optimizer.analyze_workflow(workflow_data)

                # Generate optimization suggestions
                suggestions = self.workflow_optimizer.generate_optimizations(optimization_results)

                # Apply automatic optimizations if enabled
                if self.config.get("auto_optimize", False):
                    applied_changes = self.workflow_optimizer.apply_optimizations(workflow_id, suggestions)
                    self._log_optimization_changes(workflow_id, applied_changes)

                # Store optimization results
                self._store_optimization_results(workflow_id, optimization_results, suggestions)

            except Exception as e:
                self.logger.error(f"Optimization failed for workflow {workflow_id}: {e}")

    def analyze_image(self, image_path: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze a single image for creative insights"""
        if not self.style_analyzer:
            return {"error": "Style analyzer not available"}

        try:
            analysis = self.style_analyzer.analyze_image(image_path, context or {})

            if self.reasoning_engine:
                reasoning = self.reasoning_engine.reason_about_image(analysis, context or {})
                analysis["reasoning"] = reasoning

            return analysis

        except Exception as e:
            self.logger.error(f"Image analysis failed: {e}")
            return {"error": str(e)}

    def optimize_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize a ComfyUI workflow"""
        if not self.workflow_optimizer:
            return {"error": "Workflow optimizer not available"}

        try:
            return self.workflow_optimizer.optimize_workflow(workflow_data)
        except Exception as e:
            self.logger.error(f"Workflow optimization failed: {e}")
            return {"error": str(e)}

    def start_collaborative_session(self, session_name: str, creator_id: str,
                                  participants: List[str] = None) -> str:
        """Start a new collaborative creative session"""
        if not self.session_manager:
            return None

        try:
            session_id = self.session_manager.create_session(session_name, creator_id, participants or [])
            self.active_sessions[session_id] = {
                "name": session_name,
                "creator": creator_id,
                "start_time": datetime.now(),
                "participants": participants or []
            }
            return session_id
        except Exception as e:
            self.logger.error(f"Failed to create collaborative session: {e}")
            return None

    def provide_creative_feedback(self, user_id: str, feedback_data: Dict[str, Any]) -> bool:
        """Process creative feedback for learning"""
        if not self.feedback_integrator:
            return False

        try:
            self.feedback_integrator.process_feedback(user_id, feedback_data)
            return True
        except Exception as e:
            self.logger.error(f"Feedback processing failed: {e}")
            return False

    def get_creative_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get AI-powered creative suggestions"""
        if not self.creative_assistant:
            return []

        try:
            return self.creative_assistant.get_suggestions(context)
        except Exception as e:
            self.logger.error(f"Creative suggestions failed: {e}")
            return []

    def _get_active_projects(self) -> Dict[str, Any]:
        """Get currently active creative projects"""
        # This would integrate with the main system to get active projects
        # For now, return empty dict - to be implemented based on system integration
        return {}

    def _get_active_workflows(self) -> Dict[str, Any]:
        """Get currently active workflows"""
        # This would integrate with ComfyUI bridge to get active workflows
        return {}

    def _store_analysis_results(self, project_id: str, results: Dict[str, Any]) -> None:
        """Store creative analysis results"""
        # Store in creative memory for future reference
        if project_id not in self.creative_memory:
            self.creative_memory[project_id] = {"analyses": []}

        self.creative_memory[project_id]["analyses"].append({
            "timestamp": datetime.now().isoformat(),
            "results": results
        })

    def _store_optimization_results(self, workflow_id: str, analysis: Dict[str, Any],
                                  suggestions: List[Dict[str, Any]]) -> None:
        """Store workflow optimization results"""
        # Store optimization history
        pass

    def _broadcast_suggestions(self, project_id: str, suggestions: List[Dict[str, Any]]) -> None:
        """Broadcast creative suggestions to relevant systems"""
        # This would integrate with UI systems to show suggestions
        pass

    def _log_optimization_changes(self, workflow_id: str, changes: Dict[str, Any]) -> None:
        """Log applied optimization changes"""
        self.logger.info(f"Applied optimizations to workflow {workflow_id}: {changes}")

    def _save_creative_memory(self) -> None:
        """Save creative memory to persistent storage"""
        try:
            memory_path = os.path.join(os.path.dirname(__file__), '..', 'creative_memory.json')
            with open(memory_path, 'w') as f:
                json.dump(self.creative_memory, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save creative memory: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of AI Creative Director"""
        return {
            "initialized": self.is_initialized,
            "running": self.running,
            "active_sessions": len(self.active_sessions),
            "components": {
                "reasoning_engine": self.reasoning_engine is not None,
                "creative_assistant": self.creative_assistant is not None,
                "style_analyzer": self.style_analyzer is not None,
                "workflow_optimizer": self.workflow_optimizer is not None,
                "session_manager": self.session_manager is not None,
                "feedback_integrator": self.feedback_integrator is not None
            },
            "performance_metrics": self.performance_metrics
        }

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update AI configuration"""
        try:
            self._merge_config(self.config, new_config)

            # Save updated config
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)

            # Reinitialize components if needed
            self._initialize_components()

            return True
        except Exception as e:
            self.logger.error(f"Config update failed: {e}")
            return False