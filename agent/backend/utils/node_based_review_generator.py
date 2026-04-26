"""Node-based review generation using entity statistics and LLM"""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from ..graph_db.neo4j_client import get_top_entities_by_mention_count

logger = logging.getLogger(__name__)


class NodeBasedReviewGenerator:
    """Generate review data based on entity statistics from Neo4j graph database"""

    def __init__(self):
        logger.info("NodeBasedReviewGenerator initialized with LLM support")

    def _create_llm(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                   model: Optional[str] = None):
        """Create LLM instance with optional custom configuration"""
        from ..config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

        try:
            # Debug logging for LLM configuration
            api_key_display = f"{api_key[:10]}..." if api_key and len(api_key) > 10 else (api_key or "None")
            logger.debug(f"Creating LLM for node-based review with params: api_key='{api_key_display}', "
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
            logger.debug(f"Created LLM for node-based review: {actual_model} with timeout=90s")
            return llm
        except Exception as e:
            logger.error(f"Failed to create LLM for node-based review: {e}")
            raise

    def get_entity_statistics(self, days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top entities by mention count within recent days"""
        try:
            logger.info(f"Getting top {limit} entities from last {days} days")
            entities = get_top_entities_by_mention_count(days=days, limit=limit)

            if not entities:
                logger.warning(f"No entities found for last {days} days")
                return []

            logger.info(f"Found {len(entities)} entities from last {days} days")

            # Format entity information for LLM prompt
            formatted_entities = []
            for i, entity in enumerate(entities[:limit]):
                name = entity.get("name", f"实体{i+1}")
                mention_count = entity.get("mention_count", 0)
                entity_type = entity.get("type", "unknown")
                description = entity.get("description", "")

                formatted_entities.append({
                    "name": name,
                    "mention_count": mention_count,
                    "type": entity_type,
                    "description": description,
                    "rank": i + 1
                })

            return formatted_entities

        except Exception as e:
            logger.error(f"Error getting entity statistics: {e}")
            return []

    def generate_node_based_review(self, days: int = 30, limit: int = 20,
                                  api_key: Optional[str] = None, base_url: Optional[str] = None,
                                  model: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate structured review based on entity statistics from Neo4j.

        Uses LLM to create meaningful knowledge cards and quiz questions from high-frequency entities.
        """
        logger.info(f"Generating node-based review for last {days} days, top {limit} entities")

        try:
            # 1. Get entity statistics
            entities = self.get_entity_statistics(days=days, limit=limit)
            if not entities:
                logger.warning("No entities found, generating fallback data")
                return self._generate_fallback_data(days)

            logger.info(f"Processing {len(entities)} entities for node-based review")

            # 2. Create LLM instance
            llm = self._create_llm(api_key, base_url, model)

            # 3. Format entity data for prompt
            entity_text = self._format_entities_for_prompt(entities, days)

            # 4. Create structured review prompt
            system_prompt = """你是一位专业的AI学习助手，负责从高频实体统计中提取知识并创建复习材料。

你的任务是根据实体提及频率数据，生成结构化的复习数据，包含：

1. 总体总结（aggregated_summary）：简要概括高频实体反映的核心学习主题，2-3句话
2. 复习分组（review_groups）：基于实体类别或相关性分组，每组包含：
   - 标题：宏观主题（如"Python编程"、"机器学习"、"系统架构"）
   - 描述：该主题的重要性和学习价值
   - 知识卡片：2-4个基于高频实体和上下文的简洁知识总结
   - 选择题：2-3个选择题，测试对该主题的理解

要求：
- 分组应基于宏观主题，而不是每个具体实体单独分组
- 每个分组应有2-4个知识卡片和2-3个选择题
- 知识卡片应结合实体提及频率和可能的知识点
- 选择题应测试概念理解，基于实体代表的专业知识
- 选择题应有4个选项，指定正确答案索引（0-3）
- 提供清晰的答案解析
- 标注难度级别（easy, medium, hard）

输出格式必须是有效的JSON，严格遵循以下结构："""

            user_prompt = f"""请基于以下高频实体统计（最近{days}天内的提及次数），生成结构化复习数据：

{entity_text}

请按照以下JSON格式输出：

{{
  "aggregated_summary": "基于高频实体的学习主题总结",
  "review_groups": [
    {{
      "id": "unique_group_id_1",  // 使用英文小写和下划线，如"python_programming"
      "title": "分组标题",
      "description": "分组描述",
      "knowledge_cards": [
        {{
          "id": "card_1",
          "content": "知识卡片内容，结合实体信息创建有意义的总结"
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
1. 生成2-4个分组（根据实体类别和频率）
2. 每个分组包含2-4个知识卡片和2-3个选择题
3. 知识卡片内容应基于实体信息创建有教育价值的内容
4. 选择题应测试相关概念理解
5. 所有ID使用英文小写和下划线

现在，请生成基于实体统计的结构化复习数据："""

            # Log prompt details for debugging
            logger.debug(f"Node-based review prompt details:")
            logger.debug(f"  System prompt length: {len(system_prompt)} chars")
            logger.debug(f"  User prompt length: {len(user_prompt)} chars")
            logger.debug(f"  Entity count: {len(entities)} entities")

            # 5. Call LLM
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

            # Log response for debugging
            logger.debug(f"Node-based review LLM response received:")
            logger.debug(f"  Response length: {len(response.content)} chars")
            logger.debug(f"  Response preview: {response.content[:200]}...")

            # 6. Parse response
            try:
                # Extract JSON from response
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                result = json.loads(content)

                # Validate and enhance the result
                validated_result = self._validate_and_enhance_result(result, days, len(entities))

                logger.info(f"Successfully generated node-based review for {days} days")
                logger.info(f"  Groups: {validated_result.get('total_groups', 0)}")
                logger.info(f"  Knowledge cards: {validated_result.get('total_knowledge_cards', 0)}")
                logger.info(f"  Quiz questions: {validated_result.get('total_quiz_questions', 0)}")

                return validated_result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}. Response: {response.content[:500]}")
                return self._generate_fallback_data(days, len(entities))

        except Exception as e:
            logger.error(f"Error generating node-based review for {days} days: {e}")
            return self._generate_fallback_data(days)

    def _format_entities_for_prompt(self, entities: List[Dict[str, Any]], days: int) -> str:
        """Format entity data for LLM prompt"""
        lines = [f"最近{days}天高频实体统计（按提及次数排序）：", ""]

        for i, entity in enumerate(entities[:20]):  # Limit to top 20 for prompt
            name = entity.get("name", f"实体{i+1}")
            mention_count = entity.get("mention_count", 0)
            entity_type = entity.get("type", "未知类型")
            description = entity.get("description", "")

            line = f"{i+1}. [{name}]"
            line += f" - 类型: {entity_type}"
            line += f" - 提及次数: {mention_count}"
            if description:
                line += f" - 描述: {description}"

            lines.append(line)

        if len(entities) > 20:
            lines.append(f"...以及{len(entities)-20}个其他实体")

        return "\n".join(lines)

    def _validate_and_enhance_result(self, result: Dict[str, Any], days: int,
                                    entity_count: int) -> Dict[str, Any]:
        """Validate the LLM result and add metadata"""
        validated = {
            "generation_type": "node_based",
            "days_range": days,
            "entity_count": entity_count,
            "generated_at": datetime.utcnow().isoformat()
        }

        # Ensure aggregated_summary
        aggregated_summary = result.get("aggregated_summary", "")
        if not aggregated_summary or len(aggregated_summary.strip()) < 10:
            aggregated_summary = f"基于最近{days}天{entity_count}个高频实体的复习总结"
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
            group_id = group.get("id", f"node_group_{i+1}")
            title = group.get("title", f"高频主题 {i+1}")
            description = group.get("description", f"基于最近{days}天高频实体的学习主题")

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
                    "quiz_questions": quiz_questions,
                    "category": "node_based"  # Mark as node-based generation
                })

        validated["review_groups"] = validated_groups

        # Add summary statistics
        validated["total_groups"] = len(validated_groups)
        validated["total_knowledge_cards"] = sum(len(g["knowledge_cards"]) for g in validated_groups)
        validated["total_quiz_questions"] = sum(len(g["quiz_questions"]) for g in validated_groups)

        # Set next_review_date (24 hours from now)
        next_review = datetime.utcnow() + timedelta(days=1)
        validated["next_review_date"] = next_review.isoformat()

        # Add session count (simulated, since this is node-based not session-based)
        validated["session_count"] = max(1, entity_count // 3)  # Approximate

        return validated

    def _generate_fallback_data(self, days: int, entity_count: int = 0) -> Dict[str, Any]:
        """Generate fallback data when LLM generation fails"""
        logger.warning(f"Generating fallback node-based review data for {days} days")

        now = datetime.utcnow()
        next_review = now + timedelta(days=1)

        return {
            "generation_type": "node_based_fallback",
            "days_range": days,
            "entity_count": entity_count,
            "generated_at": now.isoformat(),
            "aggregated_summary": f"基于最近{days}天高频实体的复习数据（生成失败时回退）",
            "review_groups": [
                {
                    "id": "node_based_general",
                    "title": "高频学习主题",
                    "description": f"基于最近{days}天{entity_count}个高频实体的知识总结",
                    "knowledge_cards": [
                        {
                            "id": "node_card_1",
                            "content": f"回顾最近{days}天讨论最频繁的主题",
                            "is_learned": False
                        },
                        {
                            "id": "node_card_2",
                            "content": "注意高频实体反映的核心学习兴趣",
                            "is_learned": False
                        }
                    ],
                    "quiz_questions": [
                        {
                            "id": "node_quiz_1",
                            "question": "高频实体统计主要反映什么？",
                            "options": [
                                "学习者的主要兴趣领域",
                                "对话的随机话题",
                                "系统的技术限制",
                                "时间分配的模式"
                            ],
                            "correct_answer": 0,
                            "explanation": "高频实体统计反映用户对话中的主要学习兴趣和知识需求",
                            "difficulty": "easy",
                            "is_completed": False
                        }
                    ],
                    "category": "node_based_fallback"
                }
            ],
            "total_groups": 1,
            "total_knowledge_cards": 2,
            "total_quiz_questions": 1,
            "session_count": max(1, entity_count // 3),
            "next_review_date": next_review.isoformat()
        }


# Global instance
node_based_review_generator = NodeBasedReviewGenerator()