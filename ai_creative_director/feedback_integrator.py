"""
Feedback Integrator
Processes user feedback and learns from creative decisions for continuous improvement
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

class FeedbackIntegrator:
    """
    Processes and learns from user feedback to improve AI creative assistance
    """

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Feedback storage
        self.feedback_data = []
        self.user_profiles = {}
        self.learning_models = {}

        # Learning parameters
        self.min_feedback_samples = 10
        self.confidence_threshold = 0.7
        self.learning_rate = 0.1

        # Data persistence
        self.feedback_path = os.path.join(os.path.dirname(__file__), '..', 'feedback_data.json')
        self.models_path = os.path.join(os.path.dirname(__file__), '..', 'learning_models.json')

        # Load existing data
        self._load_feedback_data()
        self._load_learning_models()

    def process_feedback(self, user_id: str, feedback_data: Dict[str, Any]) -> bool:
        """
        Process user feedback for learning

        Args:
            user_id: User providing feedback
            feedback_data: Feedback information

        Returns:
            Success status
        """
        try:
            # Validate feedback data
            if not self._validate_feedback(feedback_data):
                return False

            # Enrich feedback with metadata
            enriched_feedback = self._enrich_feedback(user_id, feedback_data)

            # Store feedback
            self.feedback_data.append(enriched_feedback)

            # Update user profile
            self._update_user_profile(user_id, enriched_feedback)

            # Update learning models
            self._update_learning_models(enriched_feedback)

            # Save data periodically
            if len(self.feedback_data) % 50 == 0:
                self._save_feedback_data()

            self.logger.info(f"Processed feedback from user {user_id}: {feedback_data.get('type', 'unknown')}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to process feedback: {e}")
            return False

    def _validate_feedback(self, feedback_data: Dict[str, Any]) -> bool:
        """Validate feedback data structure"""
        required_fields = ["type", "rating"]

        for field in required_fields:
            if field not in feedback_data:
                return False

        # Validate rating range
        rating = feedback_data.get("rating", 0)
        if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
            return False

        return True

    def _enrich_feedback(self, user_id: str, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich feedback with additional metadata"""
        enriched = feedback_data.copy()
        enriched.update({
            "user_id": user_id,
            "timestamp": datetime.now(),
            "session_id": enriched.get("session_id"),
            "version": "1.0",
            "processed": False
        })

        # Add context information
        enriched["context"] = self._extract_context(enriched)

        return enriched

    def _extract_context(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Extract contextual information from feedback"""
        context = {
            "feedback_type": feedback.get("type"),
            "user_experience_level": self._estimate_user_experience(feedback.get("user_id")),
            "time_of_day": datetime.now().hour,
            "day_of_week": datetime.now().weekday(),
            "suggestion_category": feedback.get("suggestion_category"),
            "implementation_difficulty": feedback.get("difficulty"),
            "outcome": feedback.get("outcome", "unknown")
        }

        return context

    def _estimate_user_experience(self, user_id: str) -> str:
        """Estimate user's experience level based on feedback history"""
        user_feedback = [f for f in self.feedback_data if f.get("user_id") == user_id]

        if len(user_feedback) < 5:
            return "beginner"
        elif len(user_feedback) < 20:
            return "intermediate"
        else:
            return "advanced"

    def _update_user_profile(self, user_id: str, feedback: Dict[str, Any]) -> None:
        """Update user profile based on feedback"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                "total_feedback": 0,
                "average_rating": 0.0,
                "preferred_categories": {},
                "difficulty_preferences": {},
                "outcome_distribution": {},
                "learning_progress": 0.0,
                "first_feedback": feedback["timestamp"],
                "last_feedback": feedback["timestamp"]
            }

        profile = self.user_profiles[user_id]

        # Update statistics
        profile["total_feedback"] += 1
        profile["last_feedback"] = feedback["timestamp"]

        # Update average rating
        current_avg = profile["average_rating"]
        new_rating = feedback["rating"]
        profile["average_rating"] = (current_avg * (profile["total_feedback"] - 1) + new_rating) / profile["total_feedback"]

        # Update category preferences
        category = feedback.get("suggestion_category", "unknown")
        if category not in profile["preferred_categories"]:
            profile["preferred_categories"][category] = 0
        profile["preferred_categories"][category] += 1

        # Update difficulty preferences
        difficulty = feedback.get("difficulty", "unknown")
        if difficulty not in profile["difficulty_preferences"]:
            profile["difficulty_preferences"][difficulty] = 0
        profile["difficulty_preferences"][difficulty] += 1

        # Update outcome distribution
        outcome = feedback.get("outcome", "unknown")
        if outcome not in profile["outcome_distribution"]:
            profile["outcome_distribution"][outcome] = 0
        profile["outcome_distribution"][outcome] += 1

        # Update learning progress
        profile["learning_progress"] = self._calculate_learning_progress(profile)

    def _calculate_learning_progress(self, profile: Dict[str, Any]) -> float:
        """Calculate user's learning progress"""
        total_feedback = profile["total_feedback"]
        avg_rating = profile["average_rating"]

        # Simple progress calculation
        progress = min(1.0, (total_feedback * avg_rating) / 100.0)
        return progress

    def _update_learning_models(self, feedback: Dict[str, Any]) -> None:
        """Update learning models based on feedback"""
        feedback_type = feedback.get("type")

        if feedback_type not in self.learning_models:
            self.learning_models[feedback_type] = {
                "total_samples": 0,
                "average_rating": 0.0,
                "success_rate": 0.0,
                "category_performance": {},
                "difficulty_performance": {},
                "context_patterns": {},
                "last_updated": datetime.now()
            }

        model = self.learning_models[feedback_type]

        # Update statistics
        model["total_samples"] += 1
        current_avg = model["average_rating"]
        new_rating = feedback["rating"]
        model["average_rating"] = (current_avg * (model["total_samples"] - 1) + new_rating) / model["total_samples"]

        # Update success rate
        success_threshold = 4.0  # Ratings 4+ considered successful
        is_success = 1 if new_rating >= success_threshold else 0
        current_success = model["success_rate"]
        model["success_rate"] = (current_success * (model["total_samples"] - 1) + is_success) / model["total_samples"]

        # Update category performance
        category = feedback.get("suggestion_category", "unknown")
        if category not in model["category_performance"]:
            model["category_performance"][category] = {"total": 0, "successful": 0}

        model["category_performance"][category]["total"] += 1
        if is_success:
            model["category_performance"][category]["successful"] += 1

        # Update difficulty performance
        difficulty = feedback.get("difficulty", "unknown")
        if difficulty not in model["difficulty_performance"]:
            model["difficulty_performance"][difficulty] = {"total": 0, "successful": 0}

        model["difficulty_performance"][difficulty]["total"] += 1
        if is_success:
            model["difficulty_performance"][difficulty]["successful"] += 1

        # Update context patterns
        context = feedback.get("context", {})
        time_of_day = context.get("time_of_day", 12)
        day_of_week = context.get("day_of_week", 0)

        context_key = f"{time_of_day}_{day_of_week}"
        if context_key not in model["context_patterns"]:
            model["context_patterns"][context_key] = {"total": 0, "average_rating": 0.0}

        pattern = model["context_patterns"][context_key]
        pattern["total"] += 1
        current_avg = pattern["average_rating"]
        pattern["average_rating"] = (current_avg * (pattern["total"] - 1) + new_rating) / pattern["total"]

        model["last_updated"] = datetime.now()

    def get_personalized_suggestions(self, user_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get personalized suggestions based on user feedback history

        Args:
            user_id: User ID
            context: Current context

        Returns:
            Personalized suggestions
        """
        try:
            if user_id not in self.user_profiles:
                return []

            profile = self.user_profiles[user_id]

            # Get user's preferences
            preferred_categories = profile.get("preferred_categories", {})
            difficulty_preferences = profile.get("difficulty_preferences", {})

            # Generate personalized suggestions
            suggestions = []

            # Suggest preferred categories
            if preferred_categories:
                top_category = max(preferred_categories.items(), key=lambda x: x[1])[0]
                suggestions.append({
                    "type": "personalized",
                    "category": top_category,
                    "title": f"More {top_category} suggestions",
                    "description": f"Based on your preference for {top_category} suggestions",
                    "confidence": 0.8
                })

            # Suggest appropriate difficulty
            if difficulty_preferences:
                preferred_difficulty = max(difficulty_preferences.items(), key=lambda x: x[1])[0]
                suggestions.append({
                    "type": "personalized",
                    "category": "difficulty",
                    "title": f"{preferred_difficulty.title()} level suggestions",
                    "description": f"Tailored to your preferred {preferred_difficulty} difficulty",
                    "confidence": 0.7
                })

            # Learning-based suggestions
            learning_suggestions = self._generate_learning_suggestions(profile)
            suggestions.extend(learning_suggestions)

            return suggestions

        except Exception as e:
            self.logger.error(f"Failed to get personalized suggestions: {e}")
            return []

    def _generate_learning_suggestions(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions based on learning progress"""
        suggestions = []
        progress = profile.get("learning_progress", 0)

        if progress < 0.3:
            suggestions.append({
                "type": "learning",
                "category": "fundamentals",
                "title": "Build fundamental skills",
                "description": "Focus on basic techniques and principles",
                "confidence": 0.9
            })
        elif progress < 0.7:
            suggestions.append({
                "type": "learning",
                "category": "advanced",
                "title": "Explore advanced techniques",
                "description": "Try more complex creative approaches",
                "confidence": 0.8
            })
        else:
            suggestions.append({
                "type": "learning",
                "category": "mastery",
                "title": "Master specialized techniques",
                "description": "Deepen expertise in your strongest areas",
                "confidence": 0.7
            })

        return suggestions

    def get_feedback_insights(self, user_id: Optional[str] = None,
                            category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get insights from feedback data

        Args:
            user_id: Specific user ID (optional)
            category: Specific category (optional)

        Returns:
            Feedback insights
        """
        try:
            # Filter feedback data
            filtered_feedback = self.feedback_data

            if user_id:
                filtered_feedback = [f for f in filtered_feedback if f.get("user_id") == user_id]

            if category:
                filtered_feedback = [f for f in filtered_feedback if f.get("suggestion_category") == category]

            if not filtered_feedback:
                return {"error": "No feedback data found"}

            # Calculate insights
            insights = {
                "total_feedback": len(filtered_feedback),
                "average_rating": np.mean([f["rating"] for f in filtered_feedback]),
                "rating_distribution": self._calculate_rating_distribution(filtered_feedback),
                "category_performance": self._calculate_category_performance(filtered_feedback),
                "trend_analysis": self._analyze_feedback_trends(filtered_feedback),
                "top_suggestions": self._identify_top_suggestions(filtered_feedback)
            }

            return insights

        except Exception as e:
            self.logger.error(f"Failed to get feedback insights: {e}")
            return {"error": str(e)}

    def _calculate_rating_distribution(self, feedback_list: List[Dict[str, Any]]) -> Dict[int, int]:
        """Calculate rating distribution"""
        distribution = defaultdict(int)
        for feedback in feedback_list:
            rating = int(feedback.get("rating", 0))
            distribution[rating] += 1

        return dict(distribution)

    def _calculate_category_performance(self, feedback_list: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate performance by category"""
        category_ratings = defaultdict(list)

        for feedback in feedback_list:
            category = feedback.get("suggestion_category", "unknown")
            rating = feedback.get("rating", 0)
            category_ratings[category].append(rating)

        # Calculate average rating per category
        performance = {}
        for category, ratings in category_ratings.items():
            performance[category] = np.mean(ratings)

        return performance

    def _analyze_feedback_trends(self, feedback_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze feedback trends over time"""
        if len(feedback_list) < 5:
            return {"insufficient_data": True}

        # Sort by timestamp
        sorted_feedback = sorted(feedback_list, key=lambda x: x.get("timestamp", datetime.min))

        # Calculate moving averages
        window_size = min(10, len(sorted_feedback))
        ratings = [f.get("rating", 0) for f in sorted_feedback]

        trend = {
            "overall_trend": "stable",
            "recent_average": np.mean(ratings[-window_size:]),
            "improvement_rate": self._calculate_improvement_rate(ratings),
            "volatility": np.std(ratings)
        }

        # Determine trend direction
        if len(ratings) >= window_size * 2:
            first_half = np.mean(ratings[:window_size])
            second_half = np.mean(ratings[-window_size:])
            if second_half > first_half + 0.2:
                trend["overall_trend"] = "improving"
            elif second_half < first_half - 0.2:
                trend["overall_trend"] = "declining"

        return trend

    def _calculate_improvement_rate(self, ratings: List[float]) -> float:
        """Calculate rate of improvement in ratings"""
        if len(ratings) < 2:
            return 0.0

        # Simple linear trend
        x = np.arange(len(ratings))
        slope, _ = np.polyfit(x, ratings, 1)

        return slope

    def _identify_top_suggestions(self, feedback_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify highest-rated suggestions"""
        suggestion_ratings = defaultdict(list)

        for feedback in feedback_list:
            suggestion_type = feedback.get("type", "unknown")
            rating = feedback.get("rating", 0)
            suggestion_ratings[suggestion_type].append(rating)

        # Calculate average rating per suggestion type
        top_suggestions = []
        for suggestion_type, ratings in suggestion_ratings.items():
            if len(ratings) >= 3:  # Minimum samples
                avg_rating = np.mean(ratings)
                top_suggestions.append({
                    "type": suggestion_type,
                    "average_rating": avg_rating,
                    "total_ratings": len(ratings),
                    "confidence": min(1.0, len(ratings) / 10.0)
                })

        # Sort by average rating
        top_suggestions.sort(key=lambda x: x["average_rating"], reverse=True)
        return top_suggestions[:5]

    def get_learning_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get recommendations for improving the AI based on feedback

        Returns:
            Learning recommendations
        """
        try:
            recommendations = []

            # Analyze learning models
            for model_type, model in self.learning_models.items():
                if model["total_samples"] >= self.min_feedback_samples:
                    success_rate = model["success_rate"]

                    if success_rate < 0.6:
                        recommendations.append({
                            "type": "model_improvement",
                            "model": model_type,
                            "issue": "Low success rate",
                            "current_performance": success_rate,
                            "recommendation": f"Improve {model_type} suggestions based on user feedback",
                            "priority": "high"
                        })

                    # Check category performance
                    for category, performance in model["category_performance"].items():
                        if performance["total"] >= 5:
                            cat_success_rate = performance["successful"] / performance["total"]
                            if cat_success_rate < 0.5:
                                recommendations.append({
                                    "type": "category_improvement",
                                    "model": model_type,
                                    "category": category,
                                    "issue": "Poor category performance",
                                    "current_performance": cat_success_rate,
                                    "recommendation": f"Refine {category} suggestions in {model_type}",
                                    "priority": "medium"
                                })

            # Sort by priority
            priority_order = {"high": 0, "medium": 1, "low": 2}
            recommendations.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))

            return recommendations

        except Exception as e:
            self.logger.error(f"Failed to get learning recommendations: {e}")
            return []

    def _save_feedback_data(self) -> None:
        """Save feedback data to disk"""
        try:
            with open(self.feedback_path, 'w') as f:
                json.dump({
                    "feedback_data": self.feedback_data,
                    "user_profiles": self.user_profiles,
                    "export_timestamp": datetime.now().isoformat()
                }, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save feedback data: {e}")

    def _load_feedback_data(self) -> None:
        """Load feedback data from disk"""
        try:
            if os.path.exists(self.feedback_path):
                with open(self.feedback_path, 'r') as f:
                    data = json.load(f)
                    self.feedback_data = data.get("feedback_data", [])
                    self.user_profiles = data.get("user_profiles", {})

                # Convert timestamp strings back to datetime
                for feedback in self.feedback_data:
                    if "timestamp" in feedback and isinstance(feedback["timestamp"], str):
                        feedback["timestamp"] = datetime.fromisoformat(feedback["timestamp"])

        except Exception as e:
            self.logger.error(f"Failed to load feedback data: {e}")

    def _save_learning_models(self) -> None:
        """Save learning models to disk"""
        try:
            with open(self.models_path, 'w') as f:
                json.dump(self.learning_models, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save learning models: {e}")

    def _load_learning_models(self) -> None:
        """Load learning models from disk"""
        try:
            if os.path.exists(self.models_path):
                with open(self.models_path, 'r') as f:
                    self.learning_models = json.load(f)

        except Exception as e:
            self.logger.error(f"Failed to load learning models: {e}")

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        return self.user_profiles.get(user_id)

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get overall feedback statistics"""
        return {
            "total_feedback": len(self.feedback_data),
            "unique_users": len(self.user_profiles),
            "average_rating": np.mean([f.get("rating", 0) for f in self.feedback_data]) if self.feedback_data else 0,
            "feedback_types": self._count_feedback_types(),
            "learning_models": len(self.learning_models)
        }

    def _count_feedback_types(self) -> Dict[str, int]:
        """Count feedback by type"""
        type_counts = defaultdict(int)
        for feedback in self.feedback_data:
            feedback_type = feedback.get("type", "unknown")
            type_counts[feedback_type] += 1

        return dict(type_counts)

    def clear_old_feedback(self, days: int = 90) -> int:
        """
        Clear feedback older than specified days

        Args:
            days: Number of days to keep

        Returns:
            Number of feedback items removed
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            original_count = len(self.feedback_data)

            self.feedback_data = [
                f for f in self.feedback_data
                if f.get("timestamp", datetime.min) > cutoff_date
            ]

            removed_count = original_count - len(self.feedback_data)

            if removed_count > 0:
                self._save_feedback_data()
                self.logger.info(f"Cleared {removed_count} old feedback items")

            return removed_count

        except Exception as e:
            self.logger.error(f"Failed to clear old feedback: {e}")
            return 0