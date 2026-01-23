"""
Context Analyzer
Analyzes creative context, user intent, and project requirements
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
from collections import defaultdict, Counter

class ContextAnalyzer:
    """
    Analyzes creative context, user intent, and project requirements
    """

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Context patterns and keywords
        self.intent_patterns = {}
        self.style_keywords = {}
        self.technique_keywords = {}
        self.emotion_keywords = {}

        # Context history and learning
        self.context_history = []
        self.user_patterns = defaultdict(list)
        self.project_contexts = {}

        # Analysis cache
        self.analysis_cache = {}

        # Initialize analysis patterns
        self._initialize_patterns()

    def _initialize_patterns(self):
        """Initialize patterns for context analysis"""
        self.intent_patterns = {
            "create": [
                r"create", r"make", r"generate", r"produce", r"build", r"design"
            ],
            "edit": [
                r"edit", r"modify", r"change", r"adjust", r"improve", r"refine"
            ],
            "analyze": [
                r"analyze", r"examine", r"review", r"assess", r"evaluate"
            ],
            "optimize": [
                r"optimize", r"improve", r"enhance", r"streamline", r"efficient"
            ],
            "collaborate": [
                r"collaborate", r"share", r"team", r"group", r"together"
            ]
        }

        self.style_keywords = {
            "realistic": ["realistic", "photorealistic", "natural", "lifelike"],
            "abstract": ["abstract", "geometric", "minimal", "conceptual"],
            "vintage": ["vintage", "retro", "classic", "nostalgic"],
            "modern": ["modern", "contemporary", "sleek", "minimalist"],
            "artistic": ["artistic", "painterly", "impressionist", "expressionist"],
            "digital": ["digital", "pixel", "vector", "3d", "cgi"]
        }

        self.technique_keywords = {
            "photography": ["photography", "photo", "camera", "lens", "exposure"],
            "painting": ["painting", "brush", "canvas", "pigment", "stroke"],
            "digital_art": ["digital art", "tablet", "software", "layers", "blending"],
            "illustration": ["illustration", "drawing", "sketch", "line art"],
            "typography": ["typography", "font", "text", "lettering", "typeface"],
            "animation": ["animation", "motion", "frame", "sequence", "timeline"]
        }

        self.emotion_keywords = {
            "happy": ["happy", "joy", "cheerful", "bright", "positive"],
            "sad": ["sad", "melancholy", "dark", "somber", "gloomy"],
            "energetic": ["energetic", "dynamic", "vibrant", "lively", "bold"],
            "calm": ["calm", "peaceful", "serene", "tranquil", "soft"],
            "mysterious": ["mysterious", "intriguing", "enigmatic", "shadowy"],
            "dramatic": ["dramatic", "intense", "powerful", "striking", "bold"]
        }

    def analyze_context(self, input_text: str, user_id: Optional[str] = None,
                       project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze the creative context from input text

        Args:
            input_text: Text to analyze
            user_id: Optional user identifier for pattern learning
            project_id: Optional project identifier

        Returns:
            Context analysis results
        """
        try:
            # Check cache first
            cache_key = hash(input_text + str(user_id) + str(project_id))
            if cache_key in self.analysis_cache:
                return self.analysis_cache[cache_key]

            analysis = {
                "intent": self._analyze_intent(input_text),
                "style": self._analyze_style(input_text),
                "technique": self._analyze_technique(input_text),
                "emotion": self._analyze_emotion(input_text),
                "complexity": self._analyze_complexity(input_text),
                "urgency": self._analyze_urgency(input_text),
                "keywords": self._extract_keywords(input_text),
                "entities": self._extract_entities(input_text),
                "sentiment": self._analyze_sentiment(input_text),
                "confidence": 0.0,
                "analyzed_at": datetime.now()
            }

            # Calculate overall confidence
            analysis["confidence"] = self._calculate_confidence(analysis)

            # Learn from user patterns if user_id provided
            if user_id:
                self._learn_user_patterns(user_id, analysis)

            # Store project context if project_id provided
            if project_id:
                self._update_project_context(project_id, analysis)

            # Cache the analysis
            self.analysis_cache[cache_key] = analysis

            # Track analysis history
            self.context_history.append({
                "input_text": input_text,
                "analysis": analysis,
                "user_id": user_id,
                "project_id": project_id,
                "timestamp": datetime.now()
            })

            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze context: {e}")
            return self._get_fallback_analysis(input_text)

    def _analyze_intent(self, text: str) -> Dict[str, Any]:
        """Analyze the user's intent from the text"""
        intent_scores = {}

        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            intent_scores[intent] = score

        # Get primary intent
        primary_intent = max(intent_scores, key=intent_scores.get) if intent_scores else "unknown"
        max_score = intent_scores.get(primary_intent, 0)

        return {
            "primary": primary_intent,
            "scores": intent_scores,
            "confidence": min(1.0, max_score / 5.0)  # Normalize confidence
        }

    def _analyze_style(self, text: str) -> Dict[str, Any]:
        """Analyze artistic style preferences"""
        style_scores = {}

        for style, keywords in self.style_keywords.items():
            score = 0
            for keyword in keywords:
                matches = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))
                score += matches
            style_scores[style] = score

        # Get top styles
        sorted_styles = sorted(style_scores.items(), key=lambda x: x[1], reverse=True)
        top_styles = [style for style, score in sorted_styles if score > 0][:3]

        return {
            "primary": top_styles[0] if top_styles else "unspecified",
            "all": top_styles,
            "scores": style_scores
        }

    def _analyze_technique(self, text: str) -> Dict[str, Any]:
        """Analyze preferred techniques or mediums"""
        technique_scores = {}

        for technique, keywords in self.technique_keywords.items():
            score = 0
            for keyword in keywords:
                matches = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))
                score += matches
            technique_scores[technique] = score

        # Get top techniques
        sorted_techniques = sorted(technique_scores.items(), key=lambda x: x[1], reverse=True)
        top_techniques = [tech for tech, score in sorted_techniques if score > 0][:3]

        return {
            "primary": top_techniques[0] if top_techniques else "unspecified",
            "all": top_techniques,
            "scores": technique_scores
        }

    def _analyze_emotion(self, text: str) -> Dict[str, Any]:
        """Analyze emotional tone and mood"""
        emotion_scores = {}

        for emotion, keywords in self.emotion_keywords.items():
            score = 0
            for keyword in keywords:
                matches = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))
                score += matches
            emotion_scores[emotion] = score

        # Get dominant emotions
        sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
        dominant_emotions = [emotion for emotion, score in sorted_emotions if score > 0][:2]

        return {
            "primary": dominant_emotions[0] if dominant_emotions else "neutral",
            "all": dominant_emotions,
            "scores": emotion_scores
        }

    def _analyze_complexity(self, text: str) -> Dict[str, Any]:
        """Analyze the complexity level of the request"""
        word_count = len(text.split())
        sentence_count = len(re.split(r'[.!?]+', text))

        # Complexity indicators
        complexity_score = 0

        # Word count factor
        if word_count > 50:
            complexity_score += 0.3
        elif word_count > 20:
            complexity_score += 0.2

        # Sentence complexity
        avg_words_per_sentence = word_count / max(sentence_count, 1)
        if avg_words_per_sentence > 20:
            complexity_score += 0.3
        elif avg_words_per_sentence > 10:
            complexity_score += 0.2

        # Technical terms
        technical_indicators = ["workflow", "optimization", "integration", "architecture", "pipeline"]
        technical_count = sum(1 for term in technical_indicators if term in text.lower())
        complexity_score += min(0.4, technical_count * 0.1)

        # Determine complexity level
        if complexity_score > 0.6:
            level = "high"
        elif complexity_score > 0.3:
            level = "medium"
        else:
            level = "low"

        return {
            "level": level,
            "score": complexity_score,
            "word_count": word_count,
            "sentence_count": sentence_count
        }

    def _analyze_urgency(self, text: str) -> Dict[str, Any]:
        """Analyze urgency level of the request"""
        urgency_indicators = {
            "high": ["urgent", "asap", "immediately", "deadline", "rush", "critical"],
            "medium": ["soon", "quickly", "priority", "important", "needed"],
            "low": ["eventually", "when possible", "later", "casual"]
        }

        urgency_score = 0
        detected_indicators = []

        for level, indicators in urgency_indicators.items():
            for indicator in indicators:
                if indicator in text.lower():
                    detected_indicators.append(indicator)
                    if level == "high":
                        urgency_score += 0.4
                    elif level == "medium":
                        urgency_score += 0.2
                    else:
                        urgency_score += 0.1

        urgency_level = "low"
        if urgency_score > 0.4:
            urgency_level = "high"
        elif urgency_score > 0.2:
            urgency_level = "medium"

        return {
            "level": urgency_level,
            "score": urgency_score,
            "indicators": detected_indicators
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        # Simple keyword extraction (in real implementation, use NLP library)
        words = re.findall(r'\b\w+\b', text.lower())

        # Remove stop words (basic list)
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"}

        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        # Get most common keywords
        keyword_counts = Counter(keywords)
        top_keywords = [word for word, count in keyword_counts.most_common(10)]

        return top_keywords

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities (simplified version)"""
        entities = {
            "projects": [],
            "tools": [],
            "styles": [],
            "people": []
        }

        # Simple entity extraction patterns
        project_patterns = [r"project\s+(\w+)", r"work\s+on\s+(\w+)", r"create\s+(\w+)"]
        for pattern in project_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities["projects"].extend(matches)

        tool_patterns = [r"using\s+(\w+)", r"with\s+(\w+)", r"tool\s+(\w+)"]
        for pattern in tool_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities["tools"].extend(matches)

        # Remove duplicates
        for entity_type in entities:
            entities[entity_type] = list(set(entities[entity_type]))

        return entities

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of the text (simplified)"""
        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic", "love", "like", "best", "awesome"]
        negative_words = ["bad", "terrible", "awful", "horrible", "hate", "dislike", "worst", "poor", "disappointing"]

        positive_count = sum(1 for word in positive_words if word in text.lower())
        negative_count = sum(1 for word in negative_words if word in text.lower())

        if positive_count > negative_count:
            sentiment = "positive"
            score = min(1.0, positive_count / 5.0)
        elif negative_count > positive_count:
            sentiment = "negative"
            score = min(1.0, negative_count / 5.0)
        else:
            sentiment = "neutral"
            score = 0.5

        return {
            "sentiment": sentiment,
            "score": score,
            "positive_indicators": positive_count,
            "negative_indicators": negative_count
        }

    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall confidence in the analysis"""
        confidence_factors = []

        # Intent confidence
        confidence_factors.append(analysis["intent"]["confidence"])

        # Style confidence (based on number of matches)
        style_matches = sum(analysis["style"]["scores"].values())
        confidence_factors.append(min(1.0, style_matches / 3.0))

        # Technique confidence
        technique_matches = sum(analysis["technique"]["scores"].values())
        confidence_factors.append(min(1.0, technique_matches / 3.0))

        # Emotion confidence
        emotion_matches = sum(analysis["emotion"]["scores"].values())
        confidence_factors.append(min(1.0, emotion_matches / 2.0))

        # Average confidence
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0

    def _learn_user_patterns(self, user_id: str, analysis: Dict[str, Any]):
        """Learn patterns from user behavior"""
        self.user_patterns[user_id].append({
            "analysis": analysis,
            "timestamp": datetime.now()
        })

        # Keep only recent patterns (last 50)
        if len(self.user_patterns[user_id]) > 50:
            self.user_patterns[user_id] = self.user_patterns[user_id][-50:]

    def _update_project_context(self, project_id: str, analysis: Dict[str, Any]):
        """Update project context with new analysis"""
        if project_id not in self.project_contexts:
            self.project_contexts[project_id] = {
                "analyses": [],
                "patterns": defaultdict(int),
                "created_at": datetime.now()
            }

        context = self.project_contexts[project_id]
        context["analyses"].append(analysis)

        # Update patterns
        context["patterns"]["intent:" + analysis["intent"]["primary"]] += 1
        context["patterns"]["style:" + analysis["style"]["primary"]] += 1
        context["patterns"]["technique:" + analysis["technique"]["primary"]] += 1

        # Keep only recent analyses (last 20)
        if len(context["analyses"]) > 20:
            context["analyses"] = context["analyses"][-20:]

    def get_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Get learned patterns for a user"""
        if user_id not in self.user_patterns:
            return {"patterns": {}, "total_analyses": 0}

        patterns = self.user_patterns[user_id]
        if not patterns:
            return {"patterns": {}, "total_analyses": 0}

        # Analyze patterns
        intent_counts = Counter()
        style_counts = Counter()
        technique_counts = Counter()

        for pattern in patterns:
            analysis = pattern["analysis"]
            intent_counts[analysis["intent"]["primary"]] += 1
            style_counts[analysis["style"]["primary"]] += 1
            technique_counts[analysis["technique"]["primary"]] += 1

        return {
            "total_analyses": len(patterns),
            "preferred_intent": intent_counts.most_common(1)[0][0] if intent_counts else "unknown",
            "preferred_style": style_counts.most_common(1)[0][0] if style_counts else "unknown",
            "preferred_technique": technique_counts.most_common(1)[0][0] if technique_counts else "unknown",
            "intent_distribution": dict(intent_counts),
            "style_distribution": dict(style_counts),
            "technique_distribution": dict(technique_counts)
        }

    def get_project_context(self, project_id: str) -> Dict[str, Any]:
        """Get context information for a project"""
        if project_id not in self.project_contexts:
            return {"exists": False}

        context = self.project_contexts[project_id]

        return {
            "exists": True,
            "total_analyses": len(context["analyses"]),
            "patterns": dict(context["patterns"]),
            "created_at": context["created_at"],
            "last_updated": context["analyses"][-1]["analyzed_at"] if context["analyses"] else None
        }

    def _get_fallback_analysis(self, text: str) -> Dict[str, Any]:
        """Get fallback analysis when main analysis fails"""
        return {
            "intent": {"primary": "unknown", "confidence": 0.0},
            "style": {"primary": "unspecified"},
            "technique": {"primary": "unspecified"},
            "emotion": {"primary": "neutral"},
            "complexity": {"level": "unknown", "score": 0.0},
            "urgency": {"level": "low", "score": 0.0},
            "keywords": [],
            "entities": {"projects": [], "tools": [], "styles": [], "people": []},
            "sentiment": {"sentiment": "neutral", "score": 0.5},
            "confidence": 0.0,
            "analyzed_at": datetime.now(),
            "error": "Analysis failed, using fallback"
        }

    def get_context_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent context analysis history"""
        return self.context_history[-limit:]

    def clear_cache(self):
        """Clear analysis cache"""
        self.analysis_cache.clear()

    def save_context_data(self, filepath: str) -> bool:
        """Save context data to file"""
        try:
            data = {
                "context_history": self.context_history,
                "user_patterns": dict(self.user_patterns),
                "project_contexts": self.project_contexts,
                "export_timestamp": datetime.now().isoformat()
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            return True

        except Exception as e:
            self.logger.error(f"Failed to save context data: {e}")
            return False

    def load_context_data(self, filepath: str) -> bool:
        """Load context data from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.context_history = data.get("context_history", [])
            self.user_patterns = defaultdict(list, data.get("user_patterns", {}))
            self.project_contexts = data.get("project_contexts", {})

            return True

        except Exception as e:
            self.logger.error(f"Failed to load context data: {e}")
            return False