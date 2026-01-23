"""
Creative Assistant
Provides interactive creative guidance and suggestions for Comfy Gimpy Studio users
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import random

class CreativeAssistant:
    """
    AI-powered creative assistant that provides interactive guidance and suggestions
    """

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Creative knowledge base
        self.creative_techniques = self._load_creative_techniques()
        self.style_suggestions = self._load_style_suggestions()
        self.composition_tips = self._load_composition_tips()

        # User interaction state
        self.user_sessions = {}
        self.creative_history = {}
        self.suggestion_cache = {}

    def _load_creative_techniques(self) -> Dict[str, List[str]]:
        """Load creative techniques knowledge base"""
        return {
            "color": [
                "Use complementary colors for high contrast",
                "Create monochromatic variations for harmony",
                "Experiment with color temperature shifts",
                "Apply color grading for mood enhancement"
            ],
            "composition": [
                "Apply rule of thirds for balanced layouts",
                "Use golden ratio for natural proportions",
                "Create depth with foreground elements",
                "Experiment with unconventional cropping"
            ],
            "lighting": [
                "Use rim lighting for subject separation",
                "Create dramatic shadows for mood",
                "Experiment with colored lighting effects",
                "Combine natural and artificial light sources"
            ],
            "texture": [
                "Layer different textures for depth",
                "Use texture to guide viewer attention",
                "Create contrast between smooth and rough elements",
                "Experiment with texture overlays"
            ],
            "style": [
                "Mix different artistic styles",
                "Create personal style variations",
                "Study and adapt famous artist techniques",
                "Experiment with different mediums digitally"
            ]
        }

    def _load_style_suggestions(self) -> Dict[str, List[str]]:
        """Load style-based suggestions"""
        return {
            "minimalist": [
                "Focus on negative space usage",
                "Limit color palette to essentials",
                "Simplify forms to basic shapes",
                "Use typography as design element"
            ],
            "vintage": [
                "Apply film grain effects",
                "Use sepia or faded color tones",
                "Add texture overlays for aged look",
                "Incorporate retro design elements"
            ],
            "modern": [
                "Use clean geometric shapes",
                "Apply high contrast elements",
                "Incorporate negative space",
                "Use sans-serif typography"
            ],
            "artistic": [
                "Experiment with brush stroke effects",
                "Apply painterly filter techniques",
                "Use color blending modes creatively",
                "Incorporate artistic composition rules"
            ]
        }

    def _load_composition_tips(self) -> Dict[str, List[str]]:
        """Load composition improvement tips"""
        return {
            "balance": [
                "Distribute visual weight evenly",
                "Use color to balance composition",
                "Balance heavy and light elements",
                "Consider symmetrical vs asymmetrical approaches"
            ],
            "focus": [
                "Create clear focal points",
                "Use contrast to draw attention",
                "Guide eye movement with lines",
                "Isolate important elements"
            ],
            "flow": [
                "Create natural eye movement paths",
                "Use leading lines effectively",
                "Connect elements with visual flow",
                "Consider reading patterns"
            ],
            "depth": [
                "Layer elements for depth",
                "Use size relationships",
                "Apply atmospheric perspective",
                "Create foreground interest"
            ]
        }

    def get_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get creative suggestions based on current context

        Args:
            context: Current creative context (project type, current work, user preferences, etc.)

        Returns:
            List of creative suggestions with priorities and explanations
        """
        try:
            suggestions = []

            # Analyze context to determine suggestion types
            project_type = context.get("project_type", "general")
            current_style = context.get("current_style", "unknown")
            user_goals = context.get("goals", [])
            current_issues = context.get("issues", [])

            # Generate technique suggestions
            technique_suggestions = self._generate_technique_suggestions(context)
            suggestions.extend(technique_suggestions)

            # Generate style suggestions
            style_suggestions = self._generate_style_suggestions(current_style, context)
            suggestions.extend(style_suggestions)

            # Generate composition suggestions
            composition_suggestions = self._generate_composition_suggestions(context)
            suggestions.extend(composition_suggestions)

            # Generate goal-oriented suggestions
            goal_suggestions = self._generate_goal_suggestions(user_goals, context)
            suggestions.extend(goal_suggestions)

            # Address specific issues
            issue_suggestions = self._generate_issue_suggestions(current_issues, context)
            suggestions.extend(issue_suggestions)

            # Sort by priority and limit results
            suggestions.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
            return suggestions[:10]  # Return top 10 suggestions

        except Exception as e:
            self.logger.error(f"Failed to generate suggestions: {e}")
            return []

    def _generate_technique_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate technique-based suggestions"""
        suggestions = []
        techniques_used = context.get("techniques_used", [])

        for category, techniques in self.creative_techniques.items():
            # Suggest techniques not yet used
            unused_techniques = [t for t in techniques if t not in techniques_used]

            for technique in unused_techniques[:2]:  # Limit per category
                suggestions.append({
                    "type": "technique",
                    "category": category,
                    "title": f"Try {technique.lower()}",
                    "description": technique,
                    "priority_score": random.uniform(0.6, 0.9),
                    "difficulty": "medium",
                    "estimated_time": "15-30 minutes",
                    "tags": [category, "technique"]
                })

        return suggestions

    def _generate_style_suggestions(self, current_style: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate style-based suggestions"""
        suggestions = []

        if current_style in self.style_suggestions:
            style_tips = self.style_suggestions[current_style]

            for tip in style_tips[:3]:  # Limit suggestions
                suggestions.append({
                    "type": "style",
                    "category": "style_refinement",
                    "title": f"Enhance {current_style} style",
                    "description": tip,
                    "priority_score": random.uniform(0.7, 0.95),
                    "difficulty": "easy",
                    "estimated_time": "10-20 minutes",
                    "tags": [current_style, "style"]
                })

        # Suggest style variations
        other_styles = [s for s in self.style_suggestions.keys() if s != current_style]
        if other_styles:
            suggested_style = random.choice(other_styles)
            style_tips = self.style_suggestions[suggested_style]

            suggestions.append({
                "type": "style",
                "category": "style_exploration",
                "title": f"Experiment with {suggested_style} elements",
                "description": random.choice(style_tips),
                "priority_score": random.uniform(0.5, 0.8),
                "difficulty": "medium",
                "estimated_time": "20-45 minutes",
                "tags": [suggested_style, "style", "exploration"]
            })

        return suggestions

    def _generate_composition_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate composition improvement suggestions"""
        suggestions = []
        composition_issues = context.get("composition_issues", [])

        for category, tips in self.composition_tips.items():
            # Prioritize based on identified issues
            priority = 0.8 if category in composition_issues else 0.6

            tip = random.choice(tips)
            suggestions.append({
                "type": "composition",
                "category": category,
                "title": f"Improve {category} in composition",
                "description": tip,
                "priority_score": priority,
                "difficulty": "easy",
                "estimated_time": "5-15 minutes",
                "tags": [category, "composition"]
            })

        return suggestions

    def _generate_goal_suggestions(self, user_goals: List[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions aligned with user goals"""
        suggestions = []

        goal_mappings = {
            "professional": ["polish composition", "enhance technical quality", "create cohesive style"],
            "artistic": ["experiment with techniques", "explore creative styles", "develop personal expression"],
            "commercial": ["optimize for audience", "ensure brand consistency", "maximize visual impact"],
            "educational": ["demonstrate techniques", "show creative process", "teach design principles"],
            "personal": ["express creativity", "enjoy the process", "create meaningful work"]
        }

        for goal in user_goals:
            if goal in goal_mappings:
                goal_actions = goal_mappings[goal]

                for action in goal_actions[:2]:  # Limit per goal
                    suggestions.append({
                        "type": "goal_oriented",
                        "category": goal,
                        "title": f"Advance {goal} objective",
                        "description": f"Focus on {action} to achieve your {goal} goals",
                        "priority_score": 0.9,  # High priority for goal-aligned suggestions
                        "difficulty": "medium",
                        "estimated_time": "30-60 minutes",
                        "tags": [goal, "goals"]
                    })

        return suggestions

    def _generate_issue_suggestions(self, issues: List[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions to address specific issues"""
        suggestions = []

        issue_solutions = {
            "color_harmony": [
                "Create a cohesive color palette",
                "Use color theory principles",
                "Adjust color relationships"
            ],
            "composition_balance": [
                "Redistribute visual elements",
                "Apply rule of thirds",
                "Balance heavy and light areas"
            ],
            "focus_clarity": [
                "Strengthen focal points",
                "Reduce visual clutter",
                "Use contrast to create hierarchy"
            ],
            "style_consistency": [
                "Define consistent design elements",
                "Maintain visual coherence",
                "Create style guidelines"
            ]
        }

        for issue in issues:
            if issue in issue_solutions:
                solutions = issue_solutions[issue]

                for solution in solutions:
                    suggestions.append({
                        "type": "issue_resolution",
                        "category": issue,
                        "title": f"Address {issue.replace('_', ' ')}",
                        "description": solution,
                        "priority_score": 0.95,  # High priority for issue resolution
                        "difficulty": "medium",
                        "estimated_time": "15-45 minutes",
                        "tags": [issue, "issues"]
                    })

        return suggestions

    def generate_suggestions(self, reasoning_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate suggestions based on design reasoning analysis

        Args:
            reasoning_results: Results from design reasoning engine

        Returns:
            Targeted creative suggestions
        """
        try:
            suggestions = []

            # Extract insights from reasoning results
            weaknesses = reasoning_results.get("overall_assessment", {}).get("weaknesses", [])
            recommendations = reasoning_results.get("recommendations", [])

            # Convert recommendations to suggestions
            for rec in recommendations:
                suggestions.append({
                    "type": "analysis_based",
                    "category": rec.get("type", "general"),
                    "title": rec.get("title", "Improvement suggestion"),
                    "description": rec.get("description", ""),
                    "action_items": rec.get("action_items", []),
                    "priority_score": 0.9 if rec.get("priority") == "high" else 0.7,
                    "difficulty": "medium",
                    "estimated_time": "20-40 minutes",
                    "tags": ["analysis", rec.get("type", "general")]
                })

            # Generate additional suggestions based on weaknesses
            for weakness in weaknesses:
                if "design principles" in weakness.lower():
                    suggestions.extend(self._generate_design_principle_suggestions())
                elif "composition" in weakness.lower():
                    suggestions.extend(self._generate_composition_improvement_suggestions())
                elif "color" in weakness.lower():
                    suggestions.extend(self._generate_color_improvement_suggestions())

            return suggestions

        except Exception as e:
            self.logger.error(f"Failed to generate analysis-based suggestions: {e}")
            return []

    def _generate_design_principle_suggestions(self) -> List[Dict[str, Any]]:
        """Generate suggestions for improving design principles"""
        return [
            {
                "type": "design_principles",
                "category": "balance",
                "title": "Improve design balance",
                "description": "Apply design principles like balance, contrast, and emphasis",
                "priority_score": 0.85,
                "difficulty": "medium",
                "estimated_time": "15-30 minutes",
                "tags": ["design", "principles", "balance"]
            }
        ]

    def _generate_composition_improvement_suggestions(self) -> List[Dict[str, Any]]:
        """Generate suggestions for composition improvements"""
        return [
            {
                "type": "composition",
                "category": "rules",
                "title": "Apply composition rules",
                "description": "Use rule of thirds, golden ratio, and other composition techniques",
                "priority_score": 0.8,
                "difficulty": "easy",
                "estimated_time": "10-20 minutes",
                "tags": ["composition", "rules"]
            }
        ]

    def _generate_color_improvement_suggestions(self) -> List[Dict[str, Any]]:
        """Generate suggestions for color improvements"""
        return [
            {
                "type": "color",
                "category": "harmony",
                "title": "Enhance color harmony",
                "description": "Create better color relationships and harmonious palettes",
                "priority_score": 0.8,
                "difficulty": "medium",
                "estimated_time": "15-25 minutes",
                "tags": ["color", "harmony"]
            }
        ]

    def start_interactive_session(self, user_id: str, context: Dict[str, Any]) -> str:
        """
        Start an interactive creative guidance session

        Args:
            user_id: Unique user identifier
            context: Initial creative context

        Returns:
            Session ID for the interactive session
        """
        try:
            session_id = f"session_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            self.user_sessions[session_id] = {
                "user_id": user_id,
                "start_time": datetime.now(),
                "context": context,
                "interaction_history": [],
                "current_suggestions": [],
                "session_state": "active"
            }

            # Generate initial suggestions
            initial_suggestions = self.get_suggestions(context)
            self.user_sessions[session_id]["current_suggestions"] = initial_suggestions

            self.logger.info(f"Started interactive session {session_id} for user {user_id}")
            return session_id

        except Exception as e:
            self.logger.error(f"Failed to start interactive session: {e}")
            return None

    def interact_with_session(self, session_id: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user interaction within a creative session

        Args:
            session_id: Active session identifier
            user_input: User interaction data

        Returns:
            AI response with new suggestions and guidance
        """
        try:
            if session_id not in self.user_sessions:
                return {"error": "Session not found"}

            session = self.user_sessions[session_id]

            # Record interaction
            interaction = {
                "timestamp": datetime.now().isoformat(),
                "input": user_input,
                "type": user_input.get("type", "general")
            }
            session["interaction_history"].append(interaction)

            # Process different interaction types
            response = self._process_interaction(session, user_input)

            # Update session context
            session["context"].update(user_input.get("context_update", {}))

            return response

        except Exception as e:
            self.logger.error(f"Session interaction failed: {e}")
            return {"error": str(e)}

    def _process_interaction(self, session: Dict[str, Any], user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process user interaction and generate response"""
        interaction_type = user_input.get("type", "general")

        if interaction_type == "suggestion_feedback":
            return self._handle_suggestion_feedback(session, user_input)
        elif interaction_type == "technique_request":
            return self._handle_technique_request(session, user_input)
        elif interaction_type == "style_exploration":
            return self._handle_style_exploration(session, user_input)
        elif interaction_type == "help_request":
            return self._handle_help_request(session, user_input)
        else:
            return self._handle_general_interaction(session, user_input)

    def _handle_suggestion_feedback(self, session: Dict[str, Any], user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle feedback on suggestions"""
        feedback = user_input.get("feedback", {})
        suggestion_id = feedback.get("suggestion_id")

        # Record feedback for learning
        self._record_feedback(session["user_id"], feedback)

        # Generate follow-up suggestions based on feedback
        new_suggestions = self._generate_followup_suggestions(session, feedback)

        return {
            "type": "feedback_response",
            "message": "Thank you for your feedback!",
            "new_suggestions": new_suggestions,
            "next_steps": self._suggest_next_steps(session, feedback)
        }

    def _handle_technique_request(self, session: Dict[str, Any], user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests for specific techniques"""
        technique_category = user_input.get("category", "general")

        techniques = self.creative_techniques.get(technique_category, [])
        selected_technique = random.choice(techniques) if techniques else "general creativity"

        return {
            "type": "technique_guidance",
            "technique": selected_technique,
            "explanation": f"Let's explore {selected_technique.lower()}",
            "steps": self._generate_technique_steps(selected_technique),
            "examples": self._generate_technique_examples(selected_technique)
        }

    def _handle_style_exploration(self, session: Dict[str, Any], user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle style exploration requests"""
        current_style = user_input.get("current_style", "unknown")
        exploration_goal = user_input.get("goal", "variety")

        suggestions = self._generate_style_suggestions(current_style, session["context"])

        return {
            "type": "style_exploration",
            "current_style": current_style,
            "exploration_goal": exploration_goal,
            "suggestions": suggestions,
            "inspiration_sources": self._suggest_inspiration_sources(current_style)
        }

    def _handle_help_request(self, session: Dict[str, Any], user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general help requests"""
        help_topic = user_input.get("topic", "general")

        return {
            "type": "help_response",
            "topic": help_topic,
            "guidance": self._generate_help_guidance(help_topic),
            "resources": self._suggest_resources(help_topic),
            "quick_tips": self._generate_quick_tips(help_topic)
        }

    def _handle_general_interaction(self, session: Dict[str, Any], user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general user interactions"""
        # Generate contextual response
        context_suggestions = self.get_suggestions(session["context"])

        return {
            "type": "general_response",
            "message": "I'm here to help with your creative process!",
            "suggestions": context_suggestions[:3],  # Top 3 suggestions
            "next_questions": self._generate_followup_questions(session)
        }

    def _record_feedback(self, user_id: str, feedback: Dict[str, Any]) -> None:
        """Record user feedback for learning"""
        if user_id not in self.creative_history:
            self.creative_history[user_id] = []

        self.creative_history[user_id].append({
            "timestamp": datetime.now().isoformat(),
            "feedback": feedback
        })

    def _generate_followup_suggestions(self, session: Dict[str, Any], feedback: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate follow-up suggestions based on feedback"""
        # This would use feedback to refine suggestions
        return self.get_suggestions(session["context"])[:2]

    def _suggest_next_steps(self, session: Dict[str, Any], feedback: Dict[str, Any]) -> List[str]:
        """Suggest next steps based on feedback"""
        return [
            "Apply the suggested technique to your current work",
            "Experiment with the recommended style variations",
            "Review your progress and provide more feedback"
        ]

    def _generate_technique_steps(self, technique: str) -> List[str]:
        """Generate step-by-step instructions for a technique"""
        # This would provide detailed steps for implementing techniques
        return [
            "Understand the basic principle",
            "Apply it to your current work",
            "Experiment with variations",
            "Evaluate the results"
        ]

    def _generate_technique_examples(self, technique: str) -> List[str]:
        """Generate examples of technique application"""
        return [
            "Example 1: Basic application",
            "Example 2: Advanced usage",
            "Example 3: Creative variation"
        ]

    def _suggest_inspiration_sources(self, style: str) -> List[str]:
        """Suggest inspiration sources for style exploration"""
        return [
            f"Study {style} artists and their techniques",
            "Explore nature for organic inspiration",
            "Look at current design trends",
            "Experiment with different mediums"
        ]

    def _generate_help_guidance(self, topic: str) -> str:
        """Generate help guidance for specific topics"""
        guidance_map = {
            "composition": "Composition is about arranging elements effectively. Focus on balance, flow, and visual hierarchy.",
            "color": "Color theory helps create harmonious palettes. Consider complementary, analogous, and triadic relationships.",
            "style": "Developing a personal style takes time. Study various approaches and combine elements you enjoy.",
            "technique": "Different techniques serve different purposes. Choose based on your goals and experiment freely."
        }

        return guidance_map.get(topic, "I'm here to help with various creative aspects. What specific area interests you?")

    def _suggest_resources(self, topic: str) -> List[str]:
        """Suggest learning resources for topics"""
        return [
            f"Books about {topic}",
            f"Online tutorials for {topic}",
            f"Examples of {topic} in art/design",
            f"Exercises to practice {topic}"
        ]

    def _generate_quick_tips(self, topic: str) -> List[str]:
        """Generate quick tips for topics"""
        return [
            "Start with simple exercises",
            "Practice regularly",
            "Study examples critically",
            "Don't be afraid to experiment"
        ]

    def _generate_followup_questions(self, session: Dict[str, Any]) -> List[str]:
        """Generate contextual follow-up questions"""
        return [
            "What aspect of your project would you like to focus on?",
            "Are you looking for specific technique guidance?",
            "Would you like style suggestions or composition help?"
        ]

    def end_session(self, session_id: str) -> bool:
        """
        End an interactive creative session

        Args:
            session_id: Session to end

        Returns:
            Success status
        """
        try:
            if session_id in self.user_sessions:
                session = self.user_sessions[session_id]
                session["end_time"] = datetime.now()
                session["session_state"] = "completed"

                # Save session data for learning
                self._save_session_data(session)

                del self.user_sessions[session_id]
                self.logger.info(f"Ended session {session_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to end session {session_id}: {e}")
            return False

    def _save_session_data(self, session: Dict[str, Any]) -> None:
        """Save session data for future learning"""
        # This would save to persistent storage
        pass

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an interactive session"""
        return self.user_sessions.get(session_id)

    def get_user_creative_profile(self, user_id: str) -> Dict[str, Any]:
        """Get creative profile for a user based on interaction history"""
        history = self.creative_history.get(user_id, [])

        if not history:
            return {"profile": "new_user", "preferences": {}, "skill_level": "unknown"}

        # Analyze history to build profile
        profile = {
            "total_sessions": len([h for h in history if h.get("type") == "session_end"]),
            "preferred_techniques": self._analyze_preferred_techniques(history),
            "skill_level": self._estimate_skill_level(history),
            "creative_goals": self._identify_goals(history),
            "learning_patterns": self._analyze_learning_patterns(history)
        }

        return profile

    def _analyze_preferred_techniques(self, history: List[Dict[str, Any]]) -> List[str]:
        """Analyze user's preferred techniques"""
        # Simple analysis - would be more sophisticated in real implementation
        return ["color", "composition"]

    def _estimate_skill_level(self, history: List[Dict[str, Any]]) -> str:
        """Estimate user's skill level"""
        session_count = len(history)
        if session_count > 20:
            return "advanced"
        elif session_count > 10:
            return "intermediate"
        else:
            return "beginner"

    def _identify_goals(self, history: List[Dict[str, Any]]) -> List[str]:
        """Identify user's creative goals"""
        return ["improvement", "exploration"]

    def _analyze_learning_patterns(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's learning patterns"""
        return {"preferred_learning_style": "hands_on", "progress_rate": "steady"}