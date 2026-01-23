"""
Creative Memory
Manages long-term memory and learning for the AI Creative Director
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import hashlib

class CreativeMemory:
    """
    Manages long-term memory and learning for creative direction
    """

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Memory storage
        self.episodic_memory = []  # Specific experiences
        self.semantic_memory = {}  # General knowledge
        self.procedural_memory = {}  # How-to knowledge

        # Learning patterns
        self.user_preferences = defaultdict(dict)
        self.creative_patterns = defaultdict(list)
        self.feedback_history = deque(maxlen=1000)

        # Memory consolidation
        self.consolidation_queue = deque()
        self.memory_strength = defaultdict(float)

        # Cache for quick access
        self.memory_cache = {}

        # Initialize memory structures
        self._initialize_memory()

    def _initialize_memory(self):
        """Initialize memory structures with default knowledge"""
        # Default creative principles
        self.semantic_memory["creative_principles"] = {
            "contrast": "Use contrast to create visual interest and hierarchy",
            "balance": "Balance elements for visual stability and harmony",
            "emphasis": "Create focal points to guide viewer attention",
            "unity": "Ensure all elements work together cohesively",
            "rhythm": "Use repetition and pattern for visual flow"
        }

        # Default style knowledge
        self.semantic_memory["style_characteristics"] = {
            "minimalist": ["clean lines", "limited colors", "negative space", "simplicity"],
            "vintage": ["aged textures", "warm colors", "ornate details", "nostalgic elements"],
            "modern": ["bold geometry", "high contrast", "sans-serif typography", "flat design"],
            "artistic": ["brush strokes", "color blending", "expressive forms", "textural variety"]
        }

        # Default workflow patterns
        self.procedural_memory["workflow_optimization"] = {
            "iterative_design": ["sketch concepts", "gather feedback", "refine design", "final polish"],
            "efficient_production": ["plan workflow", "batch similar tasks", "use templates", "automate repetitive steps"],
            "quality_assurance": ["self-review", "peer feedback", "user testing", "performance metrics"]
        }

    def store_experience(self, experience: Dict[str, Any], user_id: Optional[str] = None) -> str:
        """
        Store a creative experience in episodic memory

        Args:
            experience: Experience data to store
            user_id: Optional user identifier

        Returns:
            Memory ID for retrieval
        """
        try:
            memory_id = self._generate_memory_id(experience)

            memory_entry = {
                "id": memory_id,
                "experience": experience,
                "user_id": user_id,
                "timestamp": datetime.now(),
                "strength": 1.0,
                "access_count": 0,
                "last_accessed": datetime.now(),
                "tags": self._extract_tags(experience)
            }

            self.episodic_memory.append(memory_entry)
            self.consolidation_queue.append(memory_id)

            # Update memory strength
            self.memory_strength[memory_id] = 1.0

            # Cache the memory
            self.memory_cache[memory_id] = memory_entry

            # Learn from the experience
            self._learn_from_experience(experience, user_id)

            # Limit memory size
            if len(self.episodic_memory) > 1000:
                self._consolidate_memories()

            return memory_id

        except Exception as e:
            self.logger.error(f"Failed to store experience: {e}")
            return ""

    def retrieve_experience(self, query: Dict[str, Any], user_id: Optional[str] = None,
                           limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant experiences from memory

        Args:
            query: Query parameters for retrieval
            user_id: Optional user ID to filter results
            limit: Maximum number of results to return

        Returns:
            List of relevant memories
        """
        try:
            candidates = []

            # Search episodic memory
            for memory in self.episodic_memory:
                if user_id and memory.get("user_id") != user_id:
                    continue

                relevance = self._calculate_relevance(memory, query)
                if relevance > 0.1:  # Minimum relevance threshold
                    candidates.append((memory, relevance))

            # Sort by relevance and recency
            candidates.sort(key=lambda x: (x[1], x[0]["timestamp"]), reverse=True)

            # Update access patterns
            results = []
            for memory, relevance in candidates[:limit]:
                memory["access_count"] += 1
                memory["last_accessed"] = datetime.now()
                memory["strength"] *= 1.1  # Strengthen accessed memories

                results.append({
                    "memory": memory,
                    "relevance": relevance,
                    "confidence": self._calculate_confidence(memory)
                })

            return results

        except Exception as e:
            self.logger.error(f"Failed to retrieve experience: {e}")
            return []

    def store_feedback(self, feedback: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Store feedback for learning

        Args:
            feedback: Feedback data
            context: Context in which feedback was given

        Returns:
            Success status
        """
        try:
            feedback_entry = {
                "feedback": feedback,
                "context": context,
                "timestamp": datetime.now(),
                "processed": False
            }

            self.feedback_history.append(feedback_entry)

            # Process feedback immediately for learning
            self._process_feedback(feedback, context)

            return True

        except Exception as e:
            self.logger.error(f"Failed to store feedback: {e}")
            return False

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get learned preferences for a user

        Args:
            user_id: User identifier

        Returns:
            User preferences
        """
        if user_id not in self.user_preferences:
            return {
                "styles": {},
                "techniques": {},
                "feedback_patterns": {},
                "learning_rate": 0.1
            }

        return self.user_preferences[user_id]

    def get_creative_patterns(self, pattern_type: str) -> List[Dict[str, Any]]:
        """
        Get learned creative patterns

        Args:
            pattern_type: Type of pattern to retrieve

        Returns:
            List of patterns
        """
        return self.creative_patterns.get(pattern_type, [])

    def consolidate_memories(self) -> Dict[str, Any]:
        """
        Consolidate memories to prevent overflow and strengthen important ones

        Returns:
            Consolidation results
        """
        try:
            results = {
                "memories_consolidated": 0,
                "memories_removed": 0,
                "patterns_learned": 0,
                "timestamp": datetime.now()
            }

            # Process consolidation queue
            while self.consolidation_queue:
                memory_id = self.consolidation_queue.popleft()
                self._consolidate_memory(memory_id)

            # Remove weak memories if over limit
            if len(self.episodic_memory) > 800:
                weak_memories = [m for m in self.episodic_memory if m["strength"] < 0.5]
                for memory in weak_memories[:200]:  # Remove up to 200 weak memories
                    self.episodic_memory.remove(memory)
                    results["memories_removed"] += 1

            # Extract patterns from recent experiences
            recent_experiences = [m for m in self.episodic_memory
                                if (datetime.now() - m["timestamp"]).days < 7]

            if recent_experiences:
                patterns = self._extract_patterns(recent_experiences)
                results["patterns_learned"] = len(patterns)

            results["memories_consolidated"] = len(self.consolidation_queue)

            return results

        except Exception as e:
            self.logger.error(f"Failed to consolidate memories: {e}")
            return {"error": str(e)}

    def _generate_memory_id(self, experience: Dict[str, Any]) -> str:
        """Generate unique ID for memory"""
        content = json.dumps(experience, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _extract_tags(self, experience: Dict[str, Any]) -> List[str]:
        """Extract tags from experience for indexing"""
        tags = []

        # Extract from experience content
        content = json.dumps(experience, default=str).lower()

        # Common creative tags
        tag_keywords = {
            "design": ["design", "layout", "composition"],
            "color": ["color", "palette", "hue", "saturation"],
            "typography": ["font", "text", "typography", "lettering"],
            "image": ["image", "photo", "picture", "visual"],
            "workflow": ["workflow", "process", "pipeline", "automation"],
            "feedback": ["feedback", "review", "critique", "suggestion"]
        }

        for tag, keywords in tag_keywords.items():
            if any(keyword in content for keyword in keywords):
                tags.append(tag)

        return tags

    def _calculate_relevance(self, memory: Dict[str, Any], query: Dict[str, Any]) -> float:
        """Calculate relevance of memory to query"""
        relevance = 0.0

        # Tag matching
        memory_tags = set(memory.get("tags", []))
        query_tags = set(query.get("tags", []))
        if memory_tags and query_tags:
            tag_overlap = len(memory_tags.intersection(query_tags))
            relevance += tag_overlap * 0.3

        # Content similarity (simplified)
        memory_content = json.dumps(memory["experience"], default=str).lower()
        query_content = json.dumps(query, default=str).lower()

        # Simple word overlap
        memory_words = set(memory_content.split())
        query_words = set(query_content.split())
        word_overlap = len(memory_words.intersection(query_words))
        relevance += min(0.4, word_overlap * 0.05)

        # Recency boost
        days_old = (datetime.now() - memory["timestamp"]).days
        recency_boost = max(0, 1.0 - (days_old / 30.0))  # Boost recent memories
        relevance += recency_boost * 0.2

        # Strength boost
        relevance += memory.get("strength", 1.0) * 0.1

        return min(1.0, relevance)

    def _calculate_confidence(self, memory: Dict[str, Any]) -> float:
        """Calculate confidence in memory"""
        confidence = 0.5  # Base confidence

        # Access history
        access_count = memory.get("access_count", 0)
        confidence += min(0.3, access_count * 0.05)

        # Strength
        strength = memory.get("strength", 1.0)
        confidence += strength * 0.2

        # Recency (recent memories are more reliable)
        days_old = (datetime.now() - memory["timestamp"]).days
        recency_factor = max(0, 1.0 - (days_old / 365.0))
        confidence += recency_factor * 0.1

        return min(1.0, confidence)

    def _learn_from_experience(self, experience: Dict[str, Any], user_id: Optional[str]):
        """Learn patterns from experience"""
        if not user_id:
            return

        # Update user preferences
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {
                "styles": defaultdict(float),
                "techniques": defaultdict(float),
                "feedback_patterns": defaultdict(float),
                "learning_rate": 0.1
            }

        prefs = self.user_preferences[user_id]
        learning_rate = prefs["learning_rate"]

        # Learn from style preferences
        if "style" in experience:
            style = experience["style"]
            prefs["styles"][style] += learning_rate

        # Learn from technique preferences
        if "technique" in experience:
            technique = experience["technique"]
            prefs["techniques"][technique] += learning_rate

    def _process_feedback(self, feedback: Dict[str, Any], context: Dict[str, Any]):
        """Process feedback for learning"""
        # Mark feedback as processed
        for entry in self.feedback_history:
            if not entry["processed"]:
                entry["processed"] = True
                break

        # Learn from feedback patterns
        feedback_type = feedback.get("type", "general")
        sentiment = feedback.get("sentiment", "neutral")

        # Store feedback pattern
        pattern = {
            "type": feedback_type,
            "sentiment": sentiment,
            "context": context,
            "timestamp": datetime.now()
        }

        self.creative_patterns["feedback"].append(pattern)

        # Update memory strengths based on feedback
        if context.get("memory_id"):
            memory_id = context["memory_id"]
            if sentiment == "positive":
                self.memory_strength[memory_id] *= 1.2
            elif sentiment == "negative":
                self.memory_strength[memory_id] *= 0.8

    def _consolidate_memory(self, memory_id: str):
        """Consolidate a specific memory"""
        # Find the memory
        memory = None
        for mem in self.episodic_memory:
            if mem["id"] == memory_id:
                memory = mem
                break

        if not memory:
            return

        # Strengthen frequently accessed memories
        if memory["access_count"] > 5:
            memory["strength"] = min(2.0, memory["strength"] * 1.1)

        # Decay old memories
        days_old = (datetime.now() - memory["timestamp"]).days
        if days_old > 30:
            decay_factor = 0.95 ** (days_old // 30)
            memory["strength"] *= decay_factor

    def _extract_patterns(self, experiences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract patterns from experiences"""
        patterns = []

        # Simple pattern extraction (in real implementation, use ML)
        style_counts = defaultdict(int)
        technique_counts = defaultdict(int)

        for exp in experiences:
            experience = exp["experience"]
            if "style" in experience:
                style_counts[experience["style"]] += 1
            if "technique" in experience:
                technique_counts[experience["technique"]] += 1

        # Create patterns for frequent combinations
        for style, count in style_counts.items():
            if count >= 3:  # Pattern threshold
                patterns.append({
                    "type": "style_preference",
                    "value": style,
                    "frequency": count,
                    "confidence": min(1.0, count / 10.0)
                })

        for technique, count in technique_counts.items():
            if count >= 3:
                patterns.append({
                    "type": "technique_preference",
                    "value": technique,
                    "frequency": count,
                    "confidence": min(1.0, count / 10.0)
                })

        return patterns

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return {
            "episodic_memories": len(self.episodic_memory),
            "semantic_concepts": len(self.semantic_memory),
            "procedural_knowledge": len(self.procedural_memory),
            "feedback_entries": len(self.feedback_history),
            "users_tracked": len(self.user_preferences),
            "cache_size": len(self.memory_cache),
            "oldest_memory": min([m["timestamp"] for m in self.episodic_memory]) if self.episodic_memory else None,
            "newest_memory": max([m["timestamp"] for m in self.episodic_memory]) if self.episodic_memory else None
        }

    def clear_old_memories(self, days_old: int = 90) -> int:
        """
        Clear memories older than specified days

        Args:
            days_old: Age threshold in days

        Returns:
            Number of memories removed
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        old_memories = [m for m in self.episodic_memory if m["timestamp"] < cutoff_date]

        for memory in old_memories:
            self.episodic_memory.remove(memory)
            if memory["id"] in self.memory_cache:
                del self.memory_cache[memory["id"]]
            if memory["id"] in self.memory_strength:
                del self.memory_strength[memory["id"]]

        return len(old_memories)

    def save_memory(self, filepath: str) -> bool:
        """Save memory to file"""
        try:
            data = {
                "episodic_memory": self.episodic_memory,
                "semantic_memory": self.semantic_memory,
                "procedural_memory": self.procedural_memory,
                "user_preferences": dict(self.user_preferences),
                "creative_patterns": dict(self.creative_patterns),
                "feedback_history": list(self.feedback_history),
                "memory_strength": dict(self.memory_strength),
                "export_timestamp": datetime.now().isoformat()
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            return True

        except Exception as e:
            self.logger.error(f"Failed to save memory: {e}")
            return False

    def load_memory(self, filepath: str) -> bool:
        """Load memory from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.episodic_memory = data.get("episodic_memory", [])
            self.semantic_memory = data.get("semantic_memory", {})
            self.procedural_memory = data.get("procedural_memory", {})
            self.user_preferences = defaultdict(dict, data.get("user_preferences", {}))
            self.creative_patterns = defaultdict(list, data.get("creative_patterns", {}))
            self.feedback_history = deque(data.get("feedback_history", []), maxlen=1000)
            self.memory_strength = defaultdict(float, data.get("memory_strength", {}))

            # Rebuild cache
            self.memory_cache = {m["id"]: m for m in self.episodic_memory}

            return True

        except Exception as e:
            self.logger.error(f"Failed to load memory: {e}")
            return False

    def reset_memory(self):
        """Reset all memory (for testing or fresh start)"""
        self.episodic_memory.clear()
        self.semantic_memory.clear()
        self.procedural_memory.clear()
        self.user_preferences.clear()
        self.creative_patterns.clear()
        self.feedback_history.clear()
        self.memory_strength.clear()
        self.memory_cache.clear()
        self.consolidation_queue.clear()

        # Re-initialize default knowledge
        self._initialize_memory()