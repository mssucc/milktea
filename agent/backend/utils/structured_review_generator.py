"""Structured review generation using LLM with single prompt"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)


class StructuredReviewGenerator:
    """Generate structured review data with groups, knowledge cards, and quiz questions using LLM"""

    def __init__(self):
        logger.info("StructuredReviewGenerator initialized with LLM support")

    def _create_llm(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                   model: Optional[str] = None):
        """Create LLM instance with optional custom configuration"""
        from ..config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

        try:
            # Debug logging for LLM configuration
            api_key_display = f"{api_key[:10]}..." if api_key and len(api_key) > 10 else (api_key or "None")
            logger.debug(f"Creating LLM for structured review with params: api_key='{api_key_display}', "
                        f"base_url='{base_url}', model='{model}'")
            logger.debug(f"Default config: OPENAI_BASE_URL='{OPENAI_BASE_URL}', OPENAI_MODEL='{OPENAI_MODEL}'")

            # Determine actual values to use
            actual_api_key = api_key if api_key is not None else OPENAI_API_KEY
            actual_base_url = base_url if base_url is not None else OPENAI_BASE_URL
            actual_model = model if model is not None else OPENAI_MODEL

            # Validate API key
            if not actual_api_key or actual_api_key.strip() == "":
                logger.error("API key is empty or not provided. Cannot create LLM instance.")
                raise ValueError("API key is required for LLM calls. Please provide a valid API key.")

            logger.debug(f"Actual LLM config: base_url='{actual_base_url}', model='{actual_model}', "
                        f"api_key_present={bool(actual_api_key)}")

            llm = ChatOpenAI(
                api_key=actual_api_key,
                base_url=actual_base_url,
                model=actual_model,
                temperature=0.5,  # Balanced temperature for structured generation
                max_tokens=2048,  # More tokens needed for structured output
                timeout=90.0,     # 90 seconds timeout for larger prompts
                max_retries=2,    # Retry twice for transient errors
            )
            logger.debug(f"Created LLM for structured review: {actual_model} with timeout=90s")
            return llm
        except Exception as e:
            logger.error(f"Failed to create LLM for structured review: {e}")
            raise

    def generate_structured_review(self, messages: List[Dict[str, str]], session_id: str,
                                  api_key: Optional[str] = None, base_url: Optional[str] = None,
                                  model: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate structured review data from conversation using a single LLM prompt.

        Returns structured data with groups containing knowledge cards and quiz questions.
        """
        logger.info(f"Generating structured review for session {session_id} with {len(messages)} messages")

        try:
            # Create LLM instance
            llm = self._create_llm(api_key, base_url, model)

            # Format conversation for review generation
            conversation_text = ""
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                conversation_text += f"{role}: {content}\n\n"

            # Create structured review prompt
            system_prompt = """你是一位专业的AI学习助手，负责从对话中提取知识并创建复习材料。

你的任务是分析对话内容，生成结构化的复习数据，包含：

1. 总体总结（aggregated_summary）：简要概括对话的核心内容，2-3句话
2. 复习分组（review_groups）：将相关知识点分组，每组包含：
   - 标题：宏观主题（如"Linux命令"、"Python编程"、"机器学习基础"）
   - 描述：该主题的简要说明
   - 知识卡片：2-4个关键知识点的简洁总结（每个知识点一个卡片）
   - 选择题：2-3个选择题，测试对该主题的理解

要求：
- 分组应基于宏观主题，而不是每个具体知识点单独分组
- 每个分组应有2-4个知识卡片和2-3个选择题
- 知识卡片应是对话核心内容的简洁总结，易于记忆
- 选择题应测试概念理解，而不是单纯记忆，科技常识适合出选择题
- 选择题应有4个选项，指定正确答案索引（0-3）
- 提供清晰的答案解析
- 标注难度级别（easy, medium, hard）

输出格式必须是有效的JSON，严格遵循以下结构："""

            user_prompt = f"""请分析以下对话，并生成结构化复习数据：

{conversation_text}

请按照以下JSON格式输出：

{{
  "aggregated_summary": "对话的总体总结",
  "review_groups": [
    {{
      "id": "unique_group_id_1",  // 使用英文小写和下划线，如"linux_commands"
      "title": "分组标题",
      "description": "分组描述",
      "knowledge_cards": [
        {{
          "id": "card_1",
          "content": "知识卡片内容，简洁总结一个关键知识点"
        }}
      ],
      "quiz_questions": [
        {{
          "id": "quiz_1",
          "question": "选择题问题",
          "options": ["选项A", "选项B", "选项C", "选项D"],
          "correct_answer": 0,  // 正确答案索引（0-3）
          "explanation": "答案解析",
          "difficulty": "easy"  // 或 "medium", "hard"
        }}
      ]
    }}
  ]
}}

请确保：
1. 生成2-4个分组（根据对话内容的丰富程度）
2. 每个分组包含2-4个知识卡片和2-3个选择题
3. 选择题的选项应具有区分度，避免明显错误
4. 知识卡片内容应直接来自对话的核心知识点
5. 所有ID使用英文小写和下划线

现在，请生成结构化的复习数据："""

            # Log prompt details for debugging
            logger.debug(f"Structured review prompt details:")
            logger.debug(f"  System prompt length: {len(system_prompt)} chars")
            logger.debug(f"  User prompt length: {len(user_prompt)} chars")
            logger.debug(f"  Conversation text: {len(conversation_text)} chars")

            # Call LLM
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

            # Log response for debugging
            logger.debug(f"Structured review LLM response received:")
            logger.debug(f"  Response length: {len(response.content)} chars")
            logger.debug(f"  Response preview: {response.content[:200]}...")

            # Parse response
            try:
                # Extract JSON from response
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                result = json.loads(content)

                # Validate and enhance the result
                validated_result = self._validate_and_enhance_result(result, session_id, len(messages))

                logger.info(f"Successfully generated structured review for session {session_id}")
                logger.info(f"  Groups: {validated_result.get('total_groups', 0)}")
                logger.info(f"  Knowledge cards: {validated_result.get('total_knowledge_cards', 0)}")
                logger.info(f"  Quiz questions: {validated_result.get('total_quiz_questions', 0)}")

                return validated_result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}. Response: {response.content[:500]}")
                return self._generate_fallback_data(session_id, len(messages))

        except Exception as e:
            logger.error(f"Error generating structured review for session {session_id}: {e}")
            return self._generate_fallback_data(session_id, len(messages))

    def _validate_and_enhance_result(self, result: Dict[str, Any], session_id: str,
                                    message_count: int) -> Dict[str, Any]:
        """Validate the LLM result and add metadata"""
        validated = {
            "session_id": session_id,
            "message_count": message_count,
            "generated_at": datetime.utcnow().isoformat()
        }

        # Ensure aggregated_summary
        aggregated_summary = result.get("aggregated_summary", "")
        if not aggregated_summary or len(aggregated_summary.strip()) < 10:
            aggregated_summary = f"对话总结（基于{message_count}条消息）"
        validated["aggregated_summary"] = aggregated_summary

        # Validate review_groups
        review_groups = result.get("review_groups", [])
        if not isinstance(review_groups, list):
            review_groups = []

        validated_groups = []
        for i, group in enumerate(review_groups):
            if not isinstance(group, dict):
                continue

            # Ensure group has required fields
            group_id = group.get("id", f"group_{i+1}")
            title = group.get("title", f"知识分组 {i+1}")
            description = group.get("description", f"关于{title}的讨论总结")

            # Validate knowledge_cards
            knowledge_cards_raw = group.get("knowledge_cards", [])
            if not isinstance(knowledge_cards_raw, list):
                knowledge_cards_raw = []

            knowledge_cards = []
            for j, card in enumerate(knowledge_cards_raw):
                if not isinstance(card, dict):
                    continue

                card_id = card.get("id", f"{group_id}_card_{j+1}")
                content = card.get("content", "")
                if not content or len(content.strip()) < 5:
                    continue  # Skip empty cards

                knowledge_cards.append({
                    "id": card_id,
                    "content": content.strip(),
                    "is_learned": False  # Default value
                })

            # Validate quiz_questions
            quiz_questions_raw = group.get("quiz_questions", [])
            if not isinstance(quiz_questions_raw, list):
                quiz_questions_raw = []

            quiz_questions = []
            for k, question in enumerate(quiz_questions_raw):
                if not isinstance(question, dict):
                    continue

                question_id = question.get("id", f"{group_id}_quiz_{k+1}")
                question_text = question.get("question", "")
                options = question.get("options", [])
                correct_answer = question.get("correct_answer", 0)
                explanation = question.get("explanation", "")
                difficulty = question.get("difficulty", "medium")

                # Validate required fields
                if not question_text or len(question_text.strip()) < 5:
                    continue

                if not isinstance(options, list) or len(options) < 4:
                    # Generate default options if missing
                    options = [f"选项A", f"选项B", f"选项C", f"选项D"]
                elif len(options) < 4:
                    # Pad options if less than 4
                    options = options + [f"选项{i+1}" for i in range(len(options), 4)]

                # Ensure correct_answer is within bounds
                if not isinstance(correct_answer, int) or correct_answer < 0 or correct_answer >= len(options):
                    correct_answer = 0

                if not explanation:
                    explanation = f"正确答案是选项{['A','B','C','D'][correct_answer]}"

                if difficulty not in ["easy", "medium", "hard"]:
                    difficulty = "medium"

                quiz_questions.append({
                    "id": question_id,
                    "question": question_text.strip(),
                    "options": options,
                    "correct_answer": correct_answer,
                    "explanation": explanation.strip(),
                    "difficulty": difficulty,
                    "is_completed": False  # Default value
                })

            # Only include groups with at least one knowledge card or quiz question
            if knowledge_cards or quiz_questions:
                validated_groups.append({
                    "id": group_id,
                    "title": title.strip(),
                    "description": description.strip(),
                    "knowledge_cards": knowledge_cards,
                    "quiz_questions": quiz_questions
                })

        validated["review_groups"] = validated_groups

        # Add summary statistics
        validated["total_groups"] = len(validated_groups)
        validated["total_knowledge_cards"] = sum(len(g["knowledge_cards"]) for g in validated_groups)
        validated["total_quiz_questions"] = sum(len(g["quiz_questions"]) for g in validated_groups)

        # Set next_review_date (24 hours from now)
        next_review = datetime.utcnow() + timedelta(days=1)
        validated["next_review_date"] = next_review.isoformat()

        return validated

    def _generate_fallback_data(self, session_id: str, message_count: int) -> Dict[str, Any]:
        """Generate fallback data when LLM generation fails"""
        logger.warning(f"Generating fallback structured review data for session {session_id}")

        now = datetime.utcnow()
        next_review = now + timedelta(days=1)

        return {
            "session_id": session_id,
            "message_count": message_count,
            "generated_at": now.isoformat(),
            "aggregated_summary": f"基于{message_count}条对话消息的总结（生成失败时回退数据）",
            "review_groups": [
                {
                    "id": "general_knowledge",
                    "title": "通用知识",
                    "description": "对话中的核心知识点总结",
                    "knowledge_cards": [
                        {
                            "id": "fallback_card_1",
                            "content": "请回顾对话中的主要讨论内容",
                            "is_learned": False
                        },
                        {
                            "id": "fallback_card_2",
                            "content": "注意理解对话中的关键概念",
                            "is_learned": False
                        }
                    ],
                    "quiz_questions": [
                        {
                            "id": "fallback_quiz_1",
                            "question": "对话主要讨论了什么内容？",
                            "options": [
                                "技术相关话题",
                                "生活日常",
                                "娱乐休闲",
                                "工作学习"
                            ],
                            "correct_answer": 0,
                            "explanation": "对话内容以技术讨论为主",
                            "difficulty": "easy",
                            "is_completed": False
                        }
                    ]
                }
            ],
            "total_groups": 1,
            "total_knowledge_cards": 2,
            "total_quiz_questions": 1,
            "next_review_date": next_review.isoformat()
        }


# Global instance
structured_review_generator = StructuredReviewGenerator()