"""
Intelligent Automation System
AI-powered recommendations, automated workflows, and quality assurance
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics
import random
from collections import defaultdict, deque
import heapq

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Import collaborative studio components
from ..collaborative_studio import get_collaborative_studio
from .multi_modal_generator import get_multimodal_generator, GenerationRequest, ContentType, GenerationProvider
from .style_transfer_engine import get_style_transfer_engine, StyleTransferRequest
from .analytics_system import get_analytics_system


class AutomationTrigger(Enum):
    """Automation trigger types"""
    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    METRIC_BASED = "metric_based"
    USER_ACTION = "user_action"
    QUALITY_THRESHOLD = "quality_threshold"


class WorkflowStepType(Enum):
    """Workflow step types"""
    GENERATE_CONTENT = "generate_content"
    STYLE_TRANSFER = "style_transfer"
    QUALITY_CHECK = "quality_check"
    NOTIFICATION = "notification"
    CONDITIONAL_BRANCH = "conditional_branch"
    DELAY = "delay"
    CUSTOM_ACTION = "custom_action"


class QualityMetric(Enum):
    """Quality assessment metrics"""
    TEXT_COHERENCE = "text_coherence"
    IMAGE_CLARITY = "image_clarity"
    AUDIO_QUALITY = "audio_quality"
    STYLE_CONSISTENCY = "style_consistency"
    CREATIVITY_SCORE = "creativity_score"
    RELEVANCE_SCORE = "relevance_score"


@dataclass
class WorkflowStep:
    """Workflow step definition"""
    step_id: str
    step_type: WorkflowStepType
    name: str
    description: str
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # Step IDs this depends on
    timeout: Optional[int] = None  # Timeout in seconds
    retry_count: int = 0
    on_failure: Optional[str] = None  # Next step on failure

    def can_execute(self, completed_steps: List[str]) -> bool:
        """Check if step can be executed"""
        return all(dep in completed_steps for dep in self.dependencies)


@dataclass
class WorkflowExecution:
    """Workflow execution instance"""
    execution_id: str
    workflow_id: str
    user_id: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    step_results: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def start(self):
        """Mark execution as started"""
        self.status = "running"
        self.started_at = datetime.now()

    def complete(self, success: bool = True, error: Optional[str] = None):
        """Mark execution as completed"""
        self.status = "completed" if success else "failed"
        self.completed_at = datetime.now()
        if error:
            self.error_message = error

    def add_step_result(self, step_id: str, result: Any):
        """Add result for a completed step"""
        self.step_results[step_id] = result
        self.completed_steps.append(step_id)


@dataclass
class AutomationRule:
    """Automation rule definition"""
    rule_id: str
    name: str
    trigger: AutomationTrigger
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    enabled: bool = True
    priority: int = 0
    cooldown_period: int = 0  # Seconds between rule activations
    last_triggered: Optional[datetime] = None

    def should_trigger(self, event_data: Dict[str, Any]) -> bool:
        """Check if rule should trigger based on event data"""
        if not self.enabled:
            return False

        # Check cooldown
        if self.last_triggered:
            cooldown_end = self.last_triggered + timedelta(seconds=self.cooldown_period)
            if datetime.now() < cooldown_end:
                return False

        # Check conditions
        return self._evaluate_conditions(event_data)

    def _evaluate_conditions(self, event_data: Dict[str, Any]) -> bool:
        """Evaluate trigger conditions"""
        for condition_key, condition_value in self.conditions.items():
            if condition_key not in event_data:
                return False

            actual_value = event_data[condition_key]

            if isinstance(condition_value, dict):
                # Complex condition with operator
                operator = condition_value.get('operator', 'eq')
                expected = condition_value.get('value')

                if operator == 'eq' and actual_value != expected:
                    return False
                elif operator == 'gt' and not (actual_value > expected):
                    return False
                elif operator == 'lt' and not (actual_value < expected):
                    return False
                elif operator == 'contains' and expected not in actual_value:
                    return False
            elif actual_value != condition_value:
                return False

        return True


@dataclass
class Recommendation:
    """AI-powered recommendation"""
    recommendation_id: str
    user_id: str
    type: str
    title: str
    description: str
    confidence_score: float
    suggested_actions: List[Dict[str, Any]]
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if recommendation is expired"""
        return self.expires_at and datetime.now() > self.expires_at


@dataclass
class QualityAssessment:
    """Content quality assessment"""
    content_id: str
    content_type: ContentType
    metrics: Dict[QualityMetric, float] = field(default_factory=dict)
    overall_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=datetime.now)
    assessor_version: str = "1.0"


class WorkflowEngine:
    """Automated workflow execution engine"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Workflow definitions
        self.workflows: Dict[str, List[WorkflowStep]] = {}

        # Active executions
        self.active_executions: Dict[str, WorkflowExecution] = {}

        # Execution queue
        self.execution_queue: asyncio.Queue = asyncio.Queue()

        # Worker tasks
        self.workers: List[asyncio.Task] = []
        self.is_running = False

        # Component references
        self.studio = None
        self.generator = None
        self.style_engine = None
        self.analytics = None

    async def initialize(self):
        """Initialize workflow engine"""
        self.logger.info("Initializing workflow engine")

        # Get component references
        self.studio = get_collaborative_studio()
        self.generator = get_multimodal_generator()
        self.style_engine = get_style_transfer_engine()
        self.analytics = get_analytics_system()

        # Start workers
        self.is_running = True
        for i in range(3):  # 3 workflow workers
            worker = asyncio.create_task(self._workflow_worker(i))
            self.workers.append(worker)

        self.logger.info("Workflow engine initialized")

    async def shutdown(self):
        """Shutdown workflow engine"""
        self.logger.info("Shutting down workflow engine")

        self.is_running = False

        # Cancel workers
        for worker in self.workers:
            worker.cancel()

        await asyncio.gather(*self.workers, return_exceptions=True)

        self.logger.info("Workflow engine shutdown complete")

    def register_workflow(self, workflow_id: str, steps: List[WorkflowStep]):
        """Register a workflow definition"""
        self.workflows[workflow_id] = steps
        self.logger.info(f"Registered workflow: {workflow_id} with {len(steps)} steps")

    async def execute_workflow(self, workflow_id: str, user_id: str,
                             initial_context: Optional[Dict[str, Any]] = None) -> str:
        """Execute a workflow"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        execution = WorkflowExecution(
            execution_id=f"{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}",
            workflow_id=workflow_id,
            user_id=user_id,
            context=initial_context or {}
        )

        self.active_executions[execution.execution_id] = execution

        # Queue for execution
        await self.execution_queue.put(execution.execution_id)

        self.logger.info(f"Queued workflow execution: {execution.execution_id}")
        return execution.execution_id

    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution status"""
        return self.active_executions.get(execution_id)

    async def _workflow_worker(self, worker_id: int):
        """Workflow execution worker"""
        while self.is_running:
            try:
                # Get execution from queue
                execution_id = await self.execution_queue.get()

                if not self.is_running:
                    break

                execution = self.active_executions.get(execution_id)
                if not execution:
                    continue

                # Execute workflow
                await self._execute_workflow_instance(execution)

                self.execution_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Workflow worker error: {e}")
                await asyncio.sleep(1)

    async def _execute_workflow_instance(self, execution: WorkflowExecution):
        """Execute a workflow instance"""
        try:
            execution.start()
            workflow_steps = self.workflows[execution.workflow_id]

            # Create execution graph
            step_graph = self._build_step_graph(workflow_steps)

            # Execute steps in topological order
            while True:
                # Find next executable steps
                next_steps = [
                    step for step in workflow_steps
                    if step.can_execute(execution.completed_steps) and
                    step.step_id not in execution.completed_steps
                ]

                if not next_steps:
                    break  # No more steps to execute

                # Execute steps (could be parallel in advanced implementation)
                for step in next_steps:
                    execution.current_step = step.step_id

                    try:
                        result = await self._execute_step(step, execution)
                        execution.add_step_result(step.step_id, result)

                    except Exception as e:
                        self.logger.error(f"Step execution failed: {step.step_id} - {e}")

                        if step.on_failure:
                            # Handle failure action
                            pass
                        else:
                            execution.complete(success=False, error=str(e))
                            return

            # Mark as completed
            execution.complete(success=True)

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {execution.execution_id} - {e}")
            execution.complete(success=False, error=str(e))

    async def _execute_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Any:
        """Execute a workflow step"""
        self.logger.debug(f"Executing step: {step.step_id} ({step.step_type.value})")

        if step.step_type == WorkflowStepType.GENERATE_CONTENT:
            return await self._execute_generate_content(step, execution)

        elif step.step_type == WorkflowStepType.STYLE_TRANSFER:
            return await self._execute_style_transfer(step, execution)

        elif step.step_type == WorkflowStepType.QUALITY_CHECK:
            return await self._execute_quality_check(step, execution)

        elif step.step_type == WorkflowStepType.NOTIFICATION:
            return await self._execute_notification(step, execution)

        elif step.step_type == WorkflowStepType.CONDITIONAL_BRANCH:
            return await self._execute_conditional_branch(step, execution)

        elif step.step_type == WorkflowStepType.DELAY:
            return await self._execute_delay(step, execution)

        elif step.step_type == WorkflowStepType.CUSTOM_ACTION:
            return await self._execute_custom_action(step, execution)

        else:
            raise ValueError(f"Unknown step type: {step.step_type}")

    async def _execute_generate_content(self, step: WorkflowStep, execution: WorkflowExecution) -> Any:
        """Execute content generation step"""
        config = step.config

        request = GenerationRequest(
            request_id=f"{execution.execution_id}_{step.step_id}",
            content_type=ContentType(config['content_type']),
            prompt=config['prompt'],
            provider=GenerationProvider(config.get('provider', 'openai')),
            parameters=config.get('parameters', {}),
            user_id=execution.user_id
        )

        result = await self.generator.generate_content(request)

        # Store result in context
        execution.context[f"{step.step_id}_result"] = result

        return result

    async def _execute_style_transfer(self, step: WorkflowStep, execution: WorkflowExecution) -> Any:
        """Execute style transfer step"""
        config = step.config

        # Get content from previous step or config
        content_source = config.get('content_source', 'previous_step')
        if content_source == 'previous_step':
            content_image = execution.step_results.get(config.get('source_step'))
        else:
            content_image = config['content_image']

        request = StyleTransferRequest(
            request_id=f"{execution.execution_id}_{step.step_id}",
            content_image=content_image,
            style_reference=config['style_id'],
            parameters=config.get('parameters', {}),
            user_id=execution.user_id
        )

        result = await self.style_engine.transfer_style(request)

        # Store result in context
        execution.context[f"{step.step_id}_result"] = result

        return result

    async def _execute_quality_check(self, step: WorkflowStep, execution: WorkflowExecution) -> Any:
        """Execute quality check step"""
        config = step.config

        # Get content to check
        content = execution.step_results.get(config.get('source_step'))
        if not content:
            raise ValueError("No content found for quality check")

        # Perform quality assessment
        assessment = await self._assess_quality(content, config.get('content_type'))

        # Check threshold
        threshold = config.get('threshold', 0.7)
        passed = assessment.overall_score >= threshold

        execution.context[f"{step.step_id}_quality"] = assessment
        execution.context[f"{step.step_id}_passed"] = passed

        return {
            'assessment': assessment,
            'passed': passed
        }

    async def _execute_notification(self, step: WorkflowStep, execution: WorkflowExecution) -> Any:
        """Execute notification step"""
        config = step.config

        # Send notification (simplified)
        message = config['message'].format(**execution.context)

        self.logger.info(f"Workflow notification: {message}")

        # Could integrate with webhook system here
        return {'message': message}

    async def _execute_conditional_branch(self, step: WorkflowStep, execution: WorkflowExecution) -> Any:
        """Execute conditional branch step"""
        config = step.config

        condition = config['condition']
        # Evaluate condition (simplified)
        condition_result = eval(condition, {"__builtins__": {}}, execution.context)

        execution.context[f"{step.step_id}_branch"] = condition_result

        return {'branch_taken': condition_result}

    async def _execute_delay(self, step: WorkflowStep, execution: WorkflowExecution) -> Any:
        """Execute delay step"""
        delay_seconds = step.config.get('seconds', 1)
        await asyncio.sleep(delay_seconds)
        return {'delayed': delay_seconds}

    async def _execute_custom_action(self, step: WorkflowStep, execution: WorkflowExecution) -> Any:
        """Execute custom action step"""
        config = step.config

        # Execute custom function (simplified)
        action_name = config['action']
        params = config.get('parameters', {})

        # This would be extensible for custom actions
        self.logger.info(f"Executing custom action: {action_name}")

        return {'action': action_name, 'params': params}

    def _build_step_graph(self, steps: List[WorkflowStep]) -> Dict[str, List[str]]:
        """Build dependency graph for steps"""
        graph = defaultdict(list)

        for step in steps:
            for dep in step.dependencies:
                graph[dep].append(step.step_id)

        return graph

    async def _assess_quality(self, content: Any, content_type: str) -> QualityAssessment:
        """Assess content quality"""
        # Simplified quality assessment
        assessment = QualityAssessment(
            content_id=str(hash(str(content))),
            content_type=ContentType(content_type)
        )

        # Mock quality metrics (would use ML models in practice)
        if content_type == 'text':
            assessment.metrics = {
                QualityMetric.TEXT_COHERENCE: random.uniform(0.6, 0.95),
                QualityMetric.RELEVANCE_SCORE: random.uniform(0.7, 0.9),
                QualityMetric.CREATIVITY_SCORE: random.uniform(0.5, 0.85)
            }
        elif content_type == 'image':
            assessment.metrics = {
                QualityMetric.IMAGE_CLARITY: random.uniform(0.7, 0.95),
                QualityMetric.STYLE_CONSISTENCY: random.uniform(0.6, 0.9)
            }

        # Calculate overall score
        assessment.overall_score = statistics.mean(assessment.metrics.values())

        # Generate issues and suggestions
        if assessment.overall_score < 0.7:
            assessment.issues.append("Content quality below threshold")
            assessment.suggestions.append("Consider regenerating with different parameters")

        return assessment


class RecommendationEngine:
    """AI-powered recommendation engine"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # User behavior patterns
        self.user_patterns: Dict[str, Dict[str, Any]] = defaultdict(dict)

        # Content preferences
        self.content_preferences: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Recommendation models (simplified)
        self.recommendation_weights = {
            'style_transfer': 0.3,
            'content_generation': 0.4,
            'workflow_automation': 0.3
        }

        # Component references
        self.analytics = None

    async def initialize(self):
        """Initialize recommendation engine"""
        self.analytics = get_analytics_system()
        self.logger.info("Recommendation engine initialized")

    def update_user_pattern(self, user_id: str, action: str, data: Dict[str, Any]):
        """Update user behavior pattern"""
        if action not in self.user_patterns[user_id]:
            self.user_patterns[user_id][action] = []

        self.user_patterns[user_id][action].append({
            'timestamp': datetime.now(),
            'data': data
        })

        # Keep only recent actions
        if len(self.user_patterns[user_id][action]) > 50:
            self.user_patterns[user_id][action] = self.user_patterns[user_id][action][-50:]

    def update_content_preference(self, user_id: str, content_type: str, score: float):
        """Update content preference score"""
        self.content_preferences[user_id][content_type] = score

    async def generate_recommendations(self, user_id: str, context: Optional[Dict[str, Any]] = None) -> List[Recommendation]:
        """Generate personalized recommendations"""
        recommendations = []

        # Analyze user patterns
        patterns = self.user_patterns.get(user_id, {})

        # Style transfer recommendations
        if 'style_transfer' in patterns:
            style_transfers = patterns['style_transfer'][-10:]  # Last 10

            if len(style_transfers) >= 3:
                # Recommend similar styles
                recent_styles = [st['data'].get('style_id') for st in style_transfers]
                most_common = max(set(recent_styles), key=recent_styles.count)

                recommendations.append(Recommendation(
                    recommendation_id=f"style_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    user_id=user_id,
                    type="style_transfer",
                    title="Try Similar Style",
                    description=f"Based on your recent style transfers, try style '{most_common}' with different content",
                    confidence_score=0.8,
                    suggested_actions=[{
                        'action': 'style_transfer',
                        'style_id': most_common,
                        'reason': 'Frequently used style'
                    }]
                ))

        # Content generation recommendations
        if 'content_generation' in patterns:
            generations = patterns['content_generation'][-10:]

            if len(generations) >= 5:
                # Recommend content type based on success rate
                content_types = {}
                for gen in generations:
                    ct = gen['data'].get('content_type')
                    success = gen['data'].get('success', True)
                    if ct not in content_types:
                        content_types[ct] = {'total': 0, 'success': 0}
                    content_types[ct]['total'] += 1
                    if success:
                        content_types[ct]['success'] += 1

                # Find best performing content type
                best_type = max(content_types.items(),
                              key=lambda x: x[1]['success'] / x[1]['total'] if x[1]['total'] > 0 else 0)

                if best_type[1]['success'] / best_type[1]['total'] > 0.7:
                    recommendations.append(Recommendation(
                        recommendation_id=f"content_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        user_id=user_id,
                        type="content_generation",
                        title="Continue with Successful Content Type",
                        description=f"You're having success with {best_type[0]} generation. Try creating more!",
                        confidence_score=0.75,
                        suggested_actions=[{
                            'action': 'generate_content',
                            'content_type': best_type[0],
                            'reason': 'High success rate'
                        }]
                    ))

        # Workflow automation recommendations
        if len(patterns) > 10:  # User has done many actions
            recommendations.append(Recommendation(
                recommendation_id=f"workflow_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                type="workflow_automation",
                title="Create Automated Workflow",
                description="You've performed many manual actions. Consider creating an automated workflow!",
                confidence_score=0.6,
                suggested_actions=[{
                    'action': 'create_workflow',
                    'reason': 'High activity level suggests automation opportunity'
                }]
            ))

        return recommendations

    def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get user behavior insights"""
        patterns = self.user_patterns.get(user_id, {})
        preferences = self.content_preferences.get(user_id, {})

        insights = {
            'total_actions': sum(len(actions) for actions in patterns.values()),
            'preferred_content_types': preferences,
            'most_active_period': self._analyze_activity_patterns(patterns),
            'success_rates': self._calculate_success_rates(patterns)
        }

        return insights

    def _analyze_activity_patterns(self, patterns: Dict[str, List]) -> str:
        """Analyze user activity patterns"""
        # Simplified analysis
        if not patterns:
            return "No activity data"

        # Count actions by hour
        hourly_counts = defaultdict(int)
        for action_list in patterns.values():
            for action in action_list:
                hour = action['timestamp'].hour
                hourly_counts[hour] += 1

        if hourly_counts:
            peak_hour = max(hourly_counts.items(), key=lambda x: x[1])[0]
            return f"Most active around {peak_hour}:00"

        return "Activity pattern unclear"

    def _calculate_success_rates(self, patterns: Dict[str, List]) -> Dict[str, float]:
        """Calculate success rates for different actions"""
        success_rates = {}

        for action_type, actions in patterns.items():
            successful = sum(1 for a in actions if a['data'].get('success', True))
            total = len(actions)
            success_rates[action_type] = successful / total if total > 0 else 0

        return success_rates


class AutomationSystem:
    """Main intelligent automation system"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Sub-systems
        self.workflow_engine = WorkflowEngine()
        self.recommendation_engine = RecommendationEngine()

        # Automation rules
        self.automation_rules: Dict[str, AutomationRule] = {}

        # Quality assurance
        self.quality_thresholds = {
            QualityMetric.TEXT_COHERENCE: 0.7,
            QualityMetric.IMAGE_CLARITY: 0.75,
            QualityMetric.AUDIO_QUALITY: 0.8,
            QualityMetric.STYLE_CONSISTENCY: 0.7,
            QualityMetric.CREATIVITY_SCORE: 0.6,
            QualityMetric.RELEVANCE_SCORE: 0.7
        }

        # Event processing
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.event_processor: Optional[asyncio.Task] = None
        self.is_running = False

    async def initialize(self):
        """Initialize automation system"""
        self.logger.info("Initializing intelligent automation system")

        # Initialize sub-systems
        await self.workflow_engine.initialize()
        await self.recommendation_engine.initialize()

        # Start event processing
        self.is_running = True
        self.event_processor = asyncio.create_task(self._process_events())

        # Register default workflows
        self._register_default_workflows()

        # Register default automation rules
        self._register_default_rules()

        self.logger.info("Intelligent automation system initialized")

    async def shutdown(self):
        """Shutdown automation system"""
        self.logger.info("Shutting down intelligent automation system")

        self.is_running = False

        if self.event_processor:
            self.event_processor.cancel()
            try:
                await self.event_processor
            except asyncio.CancelledError:
                pass

        await self.workflow_engine.shutdown()

        self.logger.info("Intelligent automation system shutdown complete")

    def register_automation_rule(self, rule: AutomationRule):
        """Register automation rule"""
        self.automation_rules[rule.rule_id] = rule
        self.logger.info(f"Registered automation rule: {rule.rule_id}")

    async def trigger_event(self, event_type: str, event_data: Dict[str, Any]):
        """Trigger automation event"""
        await self.event_queue.put({
            'type': event_type,
            'data': event_data,
            'timestamp': datetime.now()
        })

    async def assess_content_quality(self, content: Any, content_type: ContentType) -> QualityAssessment:
        """Assess content quality"""
        return await self.workflow_engine._assess_quality(content, content_type.value)

    def check_quality_threshold(self, assessment: QualityAssessment) -> bool:
        """Check if content meets quality thresholds"""
        for metric, score in assessment.metrics.items():
            threshold = self.quality_thresholds.get(metric, 0.5)
            if score < threshold:
                return False
        return True

    async def get_recommendations(self, user_id: str, context: Optional[Dict[str, Any]] = None) -> List[Recommendation]:
        """Get AI-powered recommendations"""
        return await self.recommendation_engine.generate_recommendations(user_id, context)

    async def execute_workflow(self, workflow_id: str, user_id: str,
                             context: Optional[Dict[str, Any]] = None) -> str:
        """Execute automated workflow"""
        return await self.workflow_engine.execute_workflow(workflow_id, user_id, context)

    def get_workflow_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution status"""
        return self.workflow_engine.get_execution_status(execution_id)

    def update_user_behavior(self, user_id: str, action: str, data: Dict[str, Any]):
        """Update user behavior for recommendations"""
        self.recommendation_engine.update_user_pattern(user_id, action, data)

    async def _process_events(self):
        """Process automation events"""
        while self.is_running:
            try:
                event = await self.event_queue.get()

                # Process event against automation rules
                await self._evaluate_automation_rules(event)

                # Update recommendation engine
                if 'user_id' in event['data']:
                    self.update_user_behavior(
                        event['data']['user_id'],
                        event['type'],
                        event['data']
                    )

                self.event_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Event processing error: {e}")
                await asyncio.sleep(1)

    async def _evaluate_automation_rules(self, event: Dict[str, Any]):
        """Evaluate automation rules against event"""
        triggered_rules = []

        for rule in self.automation_rules.values():
            if rule.should_trigger(event['data']):
                triggered_rules.append(rule)
                rule.last_triggered = datetime.now()

        # Execute triggered rules (sorted by priority)
        triggered_rules.sort(key=lambda r: r.priority, reverse=True)

        for rule in triggered_rules:
            try:
                await self._execute_rule_actions(rule, event['data'])
            except Exception as e:
                self.logger.error(f"Rule execution error: {rule.rule_id} - {e}")

    async def _execute_rule_actions(self, rule: AutomationRule, event_data: Dict[str, Any]):
        """Execute automation rule actions"""
        for action in rule.actions:
            action_type = action.get('type')

            if action_type == 'execute_workflow':
                workflow_id = action['workflow_id']
                user_id = event_data.get('user_id')
                if user_id:
                    await self.execute_workflow(workflow_id, user_id, event_data)

            elif action_type == 'send_notification':
                # Send notification (simplified)
                self.logger.info(f"Automation notification: {action['message']}")

            elif action_type == 'update_quality_threshold':
                metric = QualityMetric(action['metric'])
                self.quality_thresholds[metric] = action['threshold']

    def _register_default_workflows(self):
        """Register default automated workflows"""
        # Content creation workflow
        content_workflow = [
            WorkflowStep(
                step_id="generate_content",
                step_type=WorkflowStepType.GENERATE_CONTENT,
                name="Generate Content",
                description="Generate initial content",
                config={
                    'content_type': 'text',
                    'prompt': '{prompt}',
                    'provider': 'openai'
                }
            ),
            WorkflowStep(
                step_id="quality_check",
                step_type=WorkflowStepType.QUALITY_CHECK,
                name="Quality Assessment",
                description="Check content quality",
                config={
                    'source_step': 'generate_content',
                    'content_type': 'text',
                    'threshold': 0.7
                },
                dependencies=["generate_content"]
            ),
            WorkflowStep(
                step_id="notification",
                step_type=WorkflowStepType.NOTIFICATION,
                name="Send Notification",
                description="Notify user of completion",
                config={
                    'message': 'Content generation completed with quality score: {quality_check.quality.overall_score:.2f}'
                },
                dependencies=["quality_check"]
            )
        ]

        self.workflow_engine.register_workflow("content_creation", content_workflow)

    def _register_default_rules(self):
        """Register default automation rules"""
        # Quality threshold rule
        quality_rule = AutomationRule(
            rule_id="quality_threshold_monitor",
            name="Quality Threshold Monitor",
            trigger=AutomationTrigger.QUALITY_THRESHOLD,
            conditions={
                'quality_score': {'operator': 'lt', 'value': 0.7}
            },
            actions=[{
                'type': 'send_notification',
                'message': 'Content quality below threshold'
            }]
        )

        self.register_automation_rule(quality_rule)

    def get_system_stats(self) -> Dict[str, Any]:
        """Get automation system statistics"""
        return {
            'active_workflows': len(self.workflow_engine.active_executions),
            'registered_workflows': len(self.workflow_engine.workflows),
            'automation_rules': len(self.automation_rules),
            'event_queue_size': self.event_queue.qsize(),
            'quality_thresholds': {k.value: v for k, v in self.quality_thresholds.items()}
        }


# Global instance
_automation_system = None

def get_automation_system() -> AutomationSystem:
    """Get global automation system instance"""
    global _automation_system
    if _automation_system is None:
        _automation_system = AutomationSystem()
    return _automation_system

async def initialize_automation_system() -> AutomationSystem:
    """Initialize the global automation system"""
    global _automation_system
    if _automation_system is None:
        _automation_system = AutomationSystem()
        await _automation_system.initialize()
    return _automation_system</content>
<parameter name="filePath">c:\Users\Baxter\Documents\ComfyUI_env\ComfyUI\custom_nodes\Comfy Gimpy Node Pack\advanced_ai\intelligent_automation.py