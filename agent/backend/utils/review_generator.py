"""Generate personalized review recommendations and spaced repetition schedules using LLM"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import json

logger = logging.getLogger(__name__)

class ReviewGenerator:
    """Generate personalized review recommendations using LLM"""

    def __init__(self):
        logger.info("ReviewGenerator initialized with LLM support")

    def _create_llm(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        """Create LLM instance with optional custom configuration"""
        from ..config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

        try:
            # Debug logging for LLM configuration
            api_key_display = f"{api_key[:10]}..." if api_key and len(api_key) > 10 else (api_key or "None")
            logger.debug(f"Creating LLM for review with params: api_key='{api_key_display}', base_url='{base_url}', model='{model}'")
            logger.debug(f"Default config: OPENAI_BASE_URL='{OPENAI_BASE_URL}', OPENAI_MODEL='{OPENAI_MODEL}'")

            # Determine actual values to use
            actual_api_key = api_key if api_key is not None else OPENAI_API_KEY
            actual_base_url = base_url if base_url is not None else OPENAI_BASE_URL
            actual_model = model if model is not None else OPENAI_MODEL

            # Validate API key
            if not actual_api_key or actual_api_key.strip() == "":
                logger.error("API key is empty or not provided. Cannot create LLM instance.")
                raise ValueError("API key is required for LLM calls. Please provide a valid API key.")

            logger.debug(f"Actual LLM config: base_url='{actual_base_url}', model='{actual_model}', api_key_present={bool(actual_api_key)}")

            llm = ChatOpenAI(
                api_key=actual_api_key,
                base_url=actual_base_url,
                model=actual_model,
                temperature=0.7,  # Higher temperature for more creative recommendations
                max_tokens=512,
                timeout=60.0,  # 60 seconds timeout for LLM calls (increased from 30)
                max_retries=2,  # Retry twice for transient errors
            )
            logger.debug(f"Created LLM for review generation: {actual_model} with timeout=60s")
            return llm
        except Exception as e:
            logger.error(f"Failed to create LLM for review generation: {e}")
            raise

    def generate_review_recommendations(self, session_id: str, recent_days: int = 3,
                                       entities: Optional[List[Dict[str, Any]]] = None,
                                       summary: Optional[str] = None,
                                       api_key: Optional[str] = None,
                                       base_url: Optional[str] = None,
                                       model: Optional[str] = None) -> Dict[str, Any]:
        """Generate personalized review recommendations for a session using LLM"""
        logger.debug(f"Generating personalized review recommendations for session: {session_id}")

        try:
            # Create LLM instance
            llm = self._create_llm(api_key, base_url, model)
            now = datetime.utcnow()

            # Prepare context for LLM
            context_parts = []
            if entities:
                entity_info = "\n".join([f"- {e.get('name', 'Unknown')} ({e.get('type', 'concept')}): {e.get('description', 'No description')}"
                                        for e in entities[:10]])  # Limit to 10 entities
                context_parts.append(f"Key entities discussed:\n{entity_info}")

            if summary:
                context_parts.append(f"Conversation summary:\n{summary}")

            context = "\n\n".join(context_parts) if context_parts else "No specific context available."

            # Create recommendation prompt
            system_prompt = """You are an expert learning coach specializing in personalized review planning.
Your task is to create personalized review recommendations based on the user's conversation.

Create 3-5 review recommendations that:
1. Address different learning modalities (reading, practice, testing, reflection)
2. Are personalized to the topics discussed
3. Have realistic time estimates (5-30 minutes)
4. Include clear priority levels (high, medium, low)
5. Suggest appropriate review intervals based on spaced repetition principles

Format your response as a JSON object with:
- "recommendations": array of recommendation objects, each with:
  - "id": sequential number
  - "type": category (quiz, summary, practice, reading, reflection, etc.)
  - "title": concise title
  - "description": detailed description
  - "estimated_time": e.g., "5 minutes", "15 minutes"
  - "due_date": ISO date string for when this should be completed
  - "priority": "high", "medium", or "low"
  - "completed": false
  - "entity_name": optional, associated entity if relevant
- "next_review_date": ISO date for the next overall review
- "learning_strategy": brief strategy description

Base due dates on spaced repetition: high priority within 1 day, medium within 3 days, low within 7 days."""

            user_prompt = f"""Create personalized review recommendations for session {session_id}.

Context from conversation:
{context}

The user had activity in the last {recent_days} days. Focus on the most important concepts for retention.

Please output valid JSON only."""

            # Log prompt details for debugging
            logger.debug(f"Review generator prompt details:")
            logger.debug(f"  System prompt length: {len(system_prompt)} chars, lines: {system_prompt.count(chr(10)) + 1}")
            logger.debug(f"  User prompt length: {len(user_prompt)} chars, context length: {len(context)} chars")
            logger.debug(f"  System prompt preview: {system_prompt[:100]}...")
            logger.debug(f"  User prompt preview: {user_prompt[:100]}...")

            # Call LLM
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

            # Log response for debugging
            logger.debug(f"Review generator LLM response received:")
            logger.debug(f"  Response length: {len(response.content)} chars")
            logger.debug(f"  Response preview: {response.content[:200]}...")

            # Parse response
            try:
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                result = json.loads(content)

                # Validate and format recommendations
                recommendations = []
                for i, rec in enumerate(result.get("recommendations", [])[:5]):  # Limit to 5
                    if not isinstance(rec, dict):
                        continue

                    # Calculate due date based on priority
                    priority = rec.get("priority", "medium").lower()
                    if priority == "high":
                        due_delta = timedelta(days=1)
                    elif priority == "low":
                        due_delta = timedelta(days=7)
                    else:  # medium
                        due_delta = timedelta(days=3)

                    recommendations.append({
                        "id": i + 1,
                        "type": rec.get("type", "review"),
                        "title": rec.get("title", f"Review Activity {i+1}"),
                        "description": rec.get("description", "Review key concepts from the conversation."),
                        "estimated_time": rec.get("estimated_time", "10 minutes"),
                        "due_date": (now + due_delta).isoformat(),
                        "priority": priority,
                        "completed": False,
                        "entity_name": rec.get("entity_name")
                    })

                # Ensure we have at least some recommendations
                if not recommendations:
                    recommendations = self._generate_placeholder_recommendations(now)

                # Determine next review date
                next_review_date = result.get("next_review_date", (now + timedelta(days=1)).isoformat())

                logger.info(f"Generated {len(recommendations)} personalized recommendations for session {session_id}")
                return {
                    "session_id": session_id,
                    "recommendations": recommendations,
                    "next_review_date": next_review_date,
                    "total_recommendations": len(recommendations),
                    "learning_strategy": result.get("learning_strategy", "Spaced repetition with varied activities")
                }

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse LLM recommendations response: {e}. Using placeholder.")
                return self._generate_placeholder_recommendations_response(session_id, now)

        except Exception as e:
            logger.error(f"Error generating review recommendations for session {session_id}: {e}")
            return self._generate_placeholder_recommendations_response(session_id, datetime.utcnow())

    def _generate_placeholder_recommendations(self, now: datetime) -> List[Dict[str, Any]]:
        """Generate placeholder recommendations when LLM fails"""
        return [
            {
                "id": 1,
                "type": "quiz",
                "title": "Key Concepts Quiz",
                "description": "Test your understanding of the main topics discussed",
                "estimated_time": "10 minutes",
                "due_date": (now + timedelta(days=1)).isoformat(),
                "priority": "high",
                "completed": False,
                "entity_name": None
            },
            {
                "id": 2,
                "type": "summary",
                "title": "Review Conversation Summary",
                "description": "Re-read the summary to reinforce key points",
                "estimated_time": "5 minutes",
                "due_date": (now + timedelta(days=3)).isoformat(),
                "priority": "medium",
                "completed": False,
                "entity_name": None
            },
            {
                "id": 3,
                "type": "practice",
                "title": "Apply Concepts",
                "description": "Try to explain the concepts in your own words",
                "estimated_time": "15 minutes",
                "due_date": (now + timedelta(days=7)).isoformat(),
                "priority": "low",
                "completed": False,
                "entity_name": None
            }
        ]

    def _generate_placeholder_recommendations_response(self, session_id: str, now: datetime) -> Dict[str, Any]:
        """Generate full placeholder response"""
        recommendations = self._generate_placeholder_recommendations(now)
        return {
            "session_id": session_id,
            "recommendations": recommendations,
            "next_review_date": (now + timedelta(days=1)).isoformat(),
            "total_recommendations": len(recommendations),
            "learning_strategy": "Basic spaced repetition"
        }

    def generate_spaced_repetition_schedule(self, knowledge_points: List[str], session_id: str,
                                           mastery_levels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate spaced repetition schedule for knowledge points"""
        logger.debug(f"Generating spaced repetition schedule for {len(knowledge_points)} points")

        now = datetime.utcnow()
        schedule = []

        for i, point in enumerate(knowledge_points[:10]):  # Limit to 10 points
            # Determine mastery level for this point
            mastery = "learning"
            if mastery_levels and point in mastery_levels:
                mastery = mastery_levels[point]

            # Adjust intervals based on mastery level
            if mastery == "mastered":
                intervals = [7, 30, 90]  # days
            elif mastery == "reviewing":
                intervals = [3, 7, 30]
            else:  # learning
                intervals = [1, 3, 7, 30]

            review_dates = [(now + timedelta(days=days)).isoformat() for days in intervals]

            schedule.append({
                "knowledge_point": point,
                "review_dates": review_dates,
                "current_stage": 0,
                "mastery_level": mastery,
                "next_review": review_dates[0] if review_dates else now.isoformat()
            })

        # Calculate overall next review date (earliest of all next reviews)
        next_reviews = [item["next_review"] for item in schedule if item["next_review"]]
        next_review = min(next_reviews) if next_reviews else (now + timedelta(days=1)).isoformat()

        return {
            "session_id": session_id,
            "schedule": schedule,
            "next_review": next_review,
            "total_points": len(schedule)
        }

# Global instance
review_generator = ReviewGenerator()