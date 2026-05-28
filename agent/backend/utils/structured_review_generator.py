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
- **分组标题必须自包含，能独立看出内容范围。** 好的标题如"豪鬼核心机制与招式"、"Pandas数据清洗常用操作"；不好的标题如"三者核心区别"、"基本概念介绍"、"重要知识点"。标题应体现具体的主体/人物/技术名称。
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

    def generate_note_review(self, markdown_content: str, note_id: str,
                             api_key: Optional[str] = None, base_url: Optional[str] = None,
                             model: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate structured review data from a markdown learning note.
        Uses the same output format as generate_structured_review.
        """
        logger.info(f"Generating note review for {note_id} ({len(markdown_content)} chars)")

        try:
            llm = self._create_llm(api_key, base_url, model)

            system_prompt = """你是一位专业的学习助教，负责将技术学习笔记转化为复习材料。

你会收到一份技术学习笔记（Markdown格式），通常包含：
- 对某个技术主题的深入分析
- 源码引用和代码片段
- 概念解释和原理推导
- 已有的Q&A

你的任务是基于笔记内容生成结构化的复习数据。重要原则：
- 基于笔记内容，但不要简单复述——要重新组织、提炼、补充关联知识
- 对于笔记中已有的Q&A，不要直接复用，而是从新的角度或更深的层次出题
- 利用你自己的知识补充笔记中没有明确写出但相关的背景知识
- 选择题应测试真正的理解，而非记忆

输出格式必须是严格有效的JSON："""

            user_prompt = f"""请分析以下技术学习笔记，生成结构化复习数据：

===== 笔记内容 =====
{markdown_content}

请按照以下JSON格式输出：

{{
  "aggregated_summary": "对笔记内容的总体概括，2-3句话，点明核心主题和关键收获",
  "review_groups": [
    {{
      "id": "unique_group_id",  // 英文小写+下划线，如"kv_cache_design"
      "title": "分组标题，体现具体技术名称，如'KV Cache的累积哈希链设计'",
      "description": "本组知识点的简要说明",
      "knowledge_cards": [
        {{
          "id": "card_1",
          "content": "知识卡片内容，简洁总结一个关键知识点。重新组织笔记内容，而非照抄原文"
        }}
      ],
      "quiz_questions": [
        {{
          "id": "quiz_1",
          "question": "选择题问题，测试理解而非记忆",
          "options": ["选项A", "选项B", "选项C", "选项D"],
          "correct_answer": 0,
          "explanation": "答案解析，说明为什么正确以及干扰项为什么错误",
          "difficulty": "medium"
        }}
      ]
    }}
  ]
}}

请确保：
1. 笔记中每个大章节（## 标题）通常对应一个review_group
2. 每个group的knowledge_cards覆盖该章节的核心知识点（2-4个）
3. 每个group的quiz_questions测试关键概念的理解（2-3个），不要与笔记中已有的Q&A完全相同
4. 利用你的知识补充背景和关联概念，让复习材料比原始笔记更丰富
5. 选择题的干扰项应有区分度，避免明显的错误选项"""

            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

            try:
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                result = json.loads(content)
                validated_result = self._validate_and_enhance_result(result, note_id, 0)

                logger.info(f"Successfully generated note review for {note_id}")
                logger.info(f"  Groups: {validated_result.get('total_groups', 0)}")
                logger.info(f"  Knowledge cards: {validated_result.get('total_knowledge_cards', 0)}")
                logger.info(f"  Quiz questions: {validated_result.get('total_quiz_questions', 0)}")

                return validated_result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                return self._generate_fallback_data(note_id, 0)

        except Exception as e:
            logger.error(f"Error generating note review for {note_id}: {e}")
            return self._generate_fallback_data(note_id, 0)

    def audit_review(self, review_data: Dict[str, Any], messages: List[Dict[str, str]],
                     api_key: Optional[str] = None, base_url: Optional[str] = None,
                     model: Optional[str] = None) -> Dict[str, Any]:
        """
        Phase 2: Independently audit generated review content against source conversation.

        Each knowledge card and quiz question is checked for factual correctness.
        Items are marked pass (keep as-is), fix (corrected version provided), or remove (drop).

        Returns the verified review data with only passing or corrected items.
        """
        review_groups = review_data.get("review_groups", [])
        total_cards = sum(len(g.get("knowledge_cards", [])) for g in review_groups)
        total_quizzes = sum(len(g.get("quiz_questions", [])) for g in review_groups)

        if not review_groups or (total_cards == 0 and total_quizzes == 0):
            logger.info("No review content to audit, skipping verification phase")
            return review_data

        logger.info(f"Auditing review: {len(review_groups)} groups, {total_cards} cards, {total_quizzes} quizzes")

        try:
            llm = self._create_llm(api_key, base_url, model)

            conversation_text = ""
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                conversation_text += f"{role}: {content}\n\n"

            review_json = json.dumps(review_groups, ensure_ascii=False, indent=2)

            system_prompt = """你是一位严格的知识审核员。你的任务是独立审核AI生成的复习内容，逐项检查其事实准确性。

你将收到：
1. 原始对话记录（source of truth）
2. AI生成的复习内容（需要审核的知识卡片和选择题）

审核原则：
- **pass（通过）**: 内容与对话事实完全一致，没有错误
- **fix（修正）**: 内容有细微错误或不精确之处，但可以修正。提供修正后的版本
- **remove（移除）**: 内容存在根本性错误、完全捏造、或无法从对话中找到依据。这类内容应当删除

审核标准：
- 知识卡片：检查每个陈述是否能在对话中找到明确依据。对话中未提及的、推测的、或错误概括的都应标记
- 选择题：检查题干是否正确、正确答案是否真的正确、干扰项是否合理、解析是否准确
- 特别注意：不要因为表述方式不同就标记为错误，只修正事实性错误
- 对于格斗游戏等专业领域，角色数据（血量、招式、帧数等）必须与对话中明确提到的完全一致

输出格式必须是严格的JSON：
{
  "audit_summary": "审核总结，2-3句话概括发现问题",
  "verified_groups": [
    // 与输入结构相同，但只包含通过审核和修正后的项目
    // 被标记为remove的项目不出现在输出中
  ]
}

对于每个知识卡片，在输出中保持不变的结构，但在需要修正时直接输出修正后的content。
对于每个选择题，同样保持结构，需要修正时修正对应字段。
不要在输出中添加审核标记字段，直接输出最终审核后的干净数据。"""

            user_prompt = f"""请严格审核以下复习内容是否与对话记录一致。

===== 原始对话记录 =====
{conversation_text}

===== 待审核的复习内容 =====
{review_json}

请逐项审核每个知识卡片和选择题：
1. 知识卡片内容是否能在对话中找到明确依据？
2. 选择题的正确答案是否真的是正确答案？解析是否准确？
3. 有没有捏造、推测、或与对话矛盾的内容？

请输出审核后的JSON，只保留通过和修正后的项目。被移除的项目直接不在输出中出现。"""

            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            audit_result = json.loads(content)
            verified_groups = audit_result.get("verified_groups", [])
            audit_summary = audit_result.get("audit_summary", "")

            # Validate the verified groups have the right structure
            validated_groups = self._validate_review_groups(verified_groups)

            # Compute statistics
            verified_cards = sum(len(g.get("knowledge_cards", [])) for g in validated_groups)
            verified_quizzes = sum(len(g.get("quiz_questions", [])) for g in validated_groups)
            removed_cards = total_cards - verified_cards
            removed_quizzes = total_quizzes - verified_quizzes

            logger.info(
                f"Audit complete: {verified_cards}/{total_cards} cards kept ({removed_cards} removed), "
                f"{verified_quizzes}/{total_quizzes} quizzes kept ({removed_quizzes} removed)"
            )
            if audit_summary:
                logger.info(f"Audit summary: {audit_summary}")

            # Update review_data with verified content
            review_data["review_groups"] = validated_groups
            review_data["total_groups"] = len(validated_groups)
            review_data["total_knowledge_cards"] = verified_cards
            review_data["total_quiz_questions"] = verified_quizzes
            review_data["audit_summary"] = audit_summary

            return review_data

        except Exception as e:
            logger.error(f"Audit phase failed: {e}, returning unverified review data")
            return review_data

    def _validate_review_groups(self, groups: List[Dict]) -> List[Dict]:
        """Validate and clean review groups without re-adding metadata (used for audit output)."""
        validated_groups = []
        for group in groups:
            if not isinstance(group, dict):
                continue

            group_id = group.get("id", "")
            title = group.get("title", "")
            description = group.get("description", "")

            if not group_id or not title:
                continue

            knowledge_cards = []
            for card in group.get("knowledge_cards", []):
                if not isinstance(card, dict):
                    continue
                content = card.get("content", "")
                if not content or len(content.strip()) < 5:
                    continue
                knowledge_cards.append({
                    "id": card.get("id", f"{group_id}_card_{len(knowledge_cards)+1}"),
                    "content": content.strip(),
                    "is_learned": False
                })

            quiz_questions = []
            for q in group.get("quiz_questions", []):
                if not isinstance(q, dict):
                    continue
                question_text = q.get("question", "")
                options = q.get("options", [])
                if not question_text or len(question_text.strip()) < 5:
                    continue
                if not isinstance(options, list) or len(options) < 2:
                    continue

                correct_answer = q.get("correct_answer", 0)
                if not isinstance(correct_answer, int) or correct_answer < 0 or correct_answer >= len(options):
                    correct_answer = 0

                quiz_questions.append({
                    "id": q.get("id", f"{group_id}_quiz_{len(quiz_questions)+1}"),
                    "question": question_text.strip(),
                    "options": options,
                    "correct_answer": correct_answer,
                    "explanation": q.get("explanation", "").strip(),
                    "difficulty": q.get("difficulty", "medium") if q.get("difficulty") in ["easy", "medium", "hard"] else "medium",
                    "is_completed": False
                })

            if knowledge_cards or quiz_questions:
                validated_groups.append({
                    "id": group_id,
                    "title": title.strip(),
                    "description": description.strip() if description else "",
                    "knowledge_cards": knowledge_cards,
                    "quiz_questions": quiz_questions
                })

        return validated_groups

    def _generate_fallback_data(self, session_id: str, message_count: int) -> Dict[str, Any]:
        """Return empty data when LLM generation fails — no placeholder content."""
        logger.warning(f"LLM generation failed for session {session_id}, returning empty review data")

        now = datetime.utcnow()
        next_review = now + timedelta(days=1)

        return {
            "session_id": session_id,
            "message_count": message_count,
            "generated_at": now.isoformat(),
            "aggregated_summary": f"复习数据生成失败（会话 {session_id}），请稍后重试",
            "review_groups": [],
            "total_groups": 0,
            "total_knowledge_cards": 0,
            "total_quiz_questions": 0,
            "next_review_date": next_review.isoformat()
        }


# Global instance
structured_review_generator = StructuredReviewGenerator()