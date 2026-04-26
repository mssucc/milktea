"""Conversation summarization and knowledge point extraction using LLM"""

import logging
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import json

logger = logging.getLogger(__name__)

class ConversationSummarizer:
    """Summarize conversations and extract key knowledge points using LLM"""

    def __init__(self):
        logger.info("ConversationSummarizer initialized with LLM support")

    def _create_llm(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        """Create LLM instance with optional custom configuration"""
        from ..config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

        try:
            # Debug logging for LLM configuration
            api_key_display = f"{api_key[:10]}..." if api_key and len(api_key) > 10 else (api_key or "None")
            logger.debug(f"Creating LLM with params: api_key='{api_key_display}', base_url='{base_url}', model='{model}'")
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
                temperature=0.3,  # Lower temperature for more consistent summaries
                max_tokens=512,
                timeout=60.0,  # 60 seconds timeout for LLM calls (increased from 30)
                max_retries=2,  # Retry twice for transient errors
            )
            logger.debug(f"Created LLM for summarization: {actual_model} with timeout=60s")
            return llm
        except Exception as e:
            logger.error(f"Failed to create LLM for summarization: {e}")
            raise

    def summarize_conversation(self, messages: List[Dict[str, str]], session_id: str,
                              api_key: Optional[str] = None, base_url: Optional[str] = None,
                              model: Optional[str] = None) -> Dict[str, Any]:
        """Summarize a conversation and extract key points using LLM"""
        logger.info(f"Summarizing conversation with {len(messages)} messages using LLM")

        try:
            # Create LLM instance
            llm = self._create_llm(api_key, base_url, model)

            # Format conversation for summarization
            conversation_text = ""
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                conversation_text += f"{role}: {content}\n\n"

            # Create summarization prompt
            system_prompt = """You are an expert educator and knowledge organizer. Your task is to:
1. Summarize the key discussion points from the conversation
2. Extract 3-5 most important knowledge points that should be reviewed
3. Identify any misunderstandings or areas needing clarification

Format your response as a JSON object with:
- "summary": A concise summary of the entire conversation (2-3 paragraphs)
- "key_points": A list of 3-5 key knowledge points to review
- "misunderstandings": Any misconceptions or unclear points (can be empty list)
- "suggested_topics": Suggested topics for deeper exploration (can be empty list)

Be concise and focus on educational value."""

            user_prompt = f"""Please analyze this conversation and provide a summary with key knowledge points:

{conversation_text}

Please output valid JSON only."""

            # Log prompt details for debugging
            logger.debug(f"Summarizer prompt details:")
            logger.debug(f"  System prompt length: {len(system_prompt)} chars, lines: {system_prompt.count(chr(10)) + 1}")
            logger.debug(f"  User prompt length: {len(user_prompt)} chars, conversation text: {len(conversation_text)} chars")
            logger.debug(f"  System prompt preview: {system_prompt[:100]}...")
            logger.debug(f"  User prompt preview: {user_prompt[:100]}...")

            # Call LLM
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

            # Log response for debugging
            logger.debug(f"Summarizer LLM response received:")
            logger.debug(f"  Response length: {len(response.content)} chars")
            logger.debug(f"  Response preview: {response.content[:200]}...")

            # Parse response
            try:
                # Extract JSON from response (handling potential markdown)
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                result = json.loads(content)

                # Ensure required fields
                if "summary" not in result:
                    result["summary"] = "Summary generated by AI."
                if "key_points" not in result:
                    result["key_points"] = ["Key points extracted from conversation."]
                if "misunderstandings" not in result:
                    result["misunderstandings"] = []
                if "suggested_topics" not in result:
                    result["suggested_topics"] = []

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}. Using fallback.")
                # Fallback to simple summary
                result = {
                    "summary": response.content[:500] + ("..." if len(response.content) > 500 else ""),
                    "key_points": ["Review the main topics discussed."],
                    "misunderstandings": [],
                    "suggested_topics": []
                }

            result["session_id"] = session_id
            result["message_count"] = len(messages)
            result["llm_model"] = model or "unknown"

            logger.info(f"Successfully summarized conversation for session {session_id}")
            return result

        except Exception as e:
            logger.error(f"Error summarizing conversation for session {session_id}: {e}")
            # Fallback to placeholder
            return {
                "summary": f"Error generating summary: {str(e)}. Please try again.",
                "key_points": ["Error occurred during summarization."],
                "misunderstandings": [],
                "suggested_topics": [],
                "session_id": session_id,
                "message_count": len(messages),
                "error": str(e)
            }

    def generate_review_questions(self, key_points: List[str], session_id: str,
                                 api_key: Optional[str] = None, base_url: Optional[str] = None,
                                 model: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate review questions based on key knowledge points using LLM"""
        logger.info(f"Generating review questions for {len(key_points)} key points using LLM")

        try:
            # Create LLM instance
            llm = self._create_llm(api_key, base_url, model)

            # Format key points for question generation
            key_points_text = "\n".join([f"- {kp}" for kp in key_points])

            # Create question generation prompt
            system_prompt = """You are an expert educator creating multiple-choice questions for knowledge review.
Create 1-2 questions per key point. Each question should:
1. Test understanding of the concept
2. Have 4 plausible options (A, B, C, D)
3. Include a clear correct answer
4. Provide a concise explanation
5. Indicate difficulty level (easy, medium, hard)

Format your response as a JSON array of question objects, each with:
- "id": sequential number (starting from 1)
- "question": the question text
- "options": list of 4 answer options
- "correct_answer": index of correct answer (0-3)
- "explanation": brief explanation of the correct answer
- "difficulty": "easy", "medium", or "hard"
- "entity_name": the key point it tests (if applicable)"""

            user_prompt = f"""Generate review questions for these key knowledge points:

{key_points_text}

Generate a total of {min(len(key_points), 3)} questions maximum.
Focus on testing conceptual understanding, not just recall.

Please output valid JSON only."""

            # Log prompt details for debugging
            logger.debug(f"Question generator prompt details:")
            logger.debug(f"  System prompt length: {len(system_prompt)} chars, lines: {system_prompt.count(chr(10)) + 1}")
            logger.debug(f"  User prompt length: {len(user_prompt)} chars, key points text: {len(key_points_text)} chars")
            logger.debug(f"  System prompt preview: {system_prompt[:100]}...")
            logger.debug(f"  User prompt preview: {user_prompt[:100]}...")

            # Call LLM
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

            # Log response for debugging
            logger.debug(f"Question generator LLM response received:")
            logger.debug(f"  Response length: {len(response.content)} chars")
            logger.debug(f"  Response preview: {response.content[:200]}...")

            # Parse response
            try:
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                questions = json.loads(content)

                # Validate and format questions
                formatted_questions = []
                for i, q in enumerate(questions[:10]):  # Limit to 10 questions
                    if not isinstance(q, dict):
                        continue

                    formatted = {
                        "id": i + 1,
                        "question": q.get("question", f"Question about key concepts {i+1}"),
                        "options": q.get("options", ["Option A", "Option B", "Option C", "Option D"]),
                        "correct_answer": min(max(int(q.get("correct_answer", 0)), 0), 3),
                        "explanation": q.get("explanation", "Explanation not provided."),
                        "difficulty": q.get("difficulty", "medium"),
                        "entity_name": q.get("entity_name", key_points[i % len(key_points)] if key_points else None)
                    }
                    formatted_questions.append(formatted)

                if not formatted_questions:
                    # Fallback to placeholder questions
                    formatted_questions = self._generate_placeholder_questions(key_points)

                logger.info(f"Generated {len(formatted_questions)} review questions for session {session_id}")
                return formatted_questions

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse LLM questions response: {e}. Using placeholder questions.")
                return self._generate_placeholder_questions(key_points)

        except Exception as e:
            logger.error(f"Error generating review questions for session {session_id}: {e}")
            return self._generate_placeholder_questions(key_points)

    def _generate_placeholder_questions(self, key_points: List[str]) -> List[Dict[str, Any]]:
        """Generate placeholder questions when LLM fails"""
        if not key_points:
            return [
                {
                    "id": 1,
                    "question": "What is Artificial Intelligence?",
                    "options": [
                        "A branch of computer science dealing with intelligent machines",
                        "A type of computer hardware",
                        "A programming language",
                        "A database system"
                    ],
                    "correct_answer": 0,
                    "explanation": "AI is the simulation of human intelligence processes by machines.",
                    "difficulty": "easy",
                    "entity_name": "Artificial Intelligence"
                }
            ]

        questions = []
        for i, point in enumerate(key_points[:5]):  # Limit to 5 questions
            questions.append({
                "id": i + 1,
                "question": f"What is {point}?",
                "options": [
                    f"A concept related to {point}",
                    f"A tool for {point}",
                    f"A type of {point} application",
                    f"A method of {point} analysis"
                ],
                "correct_answer": 0,
                "explanation": f"This question tests understanding of {point}.",
                "difficulty": "medium",
                "entity_name": point
            })
        return questions

# Global instance
conversation_summarizer = ConversationSummarizer()