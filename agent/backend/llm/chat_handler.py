from typing import List, Dict, Any, Optional, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, AIMessageChunk
from langchain_core.chat_history import InMemoryChatMessageHistory
import logging

from backend.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

logger = logging.getLogger(__name__)

class ChatHandler:
    """Handler for LLM chat interactions using OpenAI-compatible APIs"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL
        self.model = model or OPENAI_MODEL
        self.llm = None
        self.memory_store = {}  # session_id -> InMemoryChatMessageHistory

        self._init_llm()
        logger.info(f"ChatHandler initialized with model: {self.model}, base_url: {self.base_url}")

    def _init_llm(self):
        """Initialize the chat model with OpenAI-compatible API"""
        try:
            # Use the configured API key (could be empty for some providers)
            api_key = self.api_key

            self.llm = ChatOpenAI(
                api_key=api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.7,
                max_tokens=512,
                # streaming=True,  # Enable for streaming responses
            )
            logger.debug(f"Chat model '{self.model}' initialized successfully with base_url: {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to initialize chat model: {e}")
            raise

    def get_memory(self, session_id: str) -> InMemoryChatMessageHistory:
        """Get or create conversation memory for a session"""
        if session_id not in self.memory_store:
            self.memory_store[session_id] = InMemoryChatMessageHistory()
        return self.memory_store[session_id]

    async def get_response(
        self,
        message: str,
        session_id: str,
        system_prompt: str = None,
        api_key: str = None,
        base_url: str = None,
        model: str = None
    ) -> Dict[str, Any]:
        """
        Get AI response for a message in a session

        Args:
            message: User message
            session_id: Session identifier
            system_prompt: Optional system prompt

        Returns:
            Dictionary with response and metadata
        """
        try:
            # Use custom configuration if provided, otherwise use instance configuration
            use_llm = self.llm
            if api_key is not None or base_url is not None or model is not None:
                # Create a temporary LLM with custom configuration
                from langchain_openai import ChatOpenAI
                use_llm = ChatOpenAI(
                    api_key=api_key if api_key is not None else self.api_key,
                    base_url=base_url if base_url is not None else self.base_url,
                    model=model if model is not None else self.model,
                    temperature=0.7,
                    max_tokens=512,
                )
                logger.debug(f"Using custom LLM configuration: {model or self.model}")

            # Get session memory
            memory = self.get_memory(session_id)

            # Prepare messages
            messages = []

            # Add system prompt if provided
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))

            # Add conversation history
            chat_history = memory.messages
            messages.extend(chat_history)

            # Add current user message
            messages.append(HumanMessage(content=message))

            # Get response from LLM
            logger.debug(f"Calling LLM with {len(messages)} messages for session {session_id}")
            response = await use_llm.ainvoke(messages)

            ai_response = response.content

            # Save conversation to memory
            memory.add_message(HumanMessage(content=message))
            memory.add_message(AIMessage(content=ai_response))

            # Prepare result
            result = {
                "response": ai_response,
                "session_id": session_id,
                "model": model if model is not None else self.model,
                "message_count": len(chat_history) + 2,  # +2 for current exchange
            }

            logger.info(f"Generated response for session {session_id}, length: {len(ai_response)}")
            return result

        except Exception as e:
            logger.error(f"Error getting response for session {session_id}: {e}")
            # Fallback response
            return {
                "response": f"I apologize, but I encountered an error: {str(e)}. Please try again.",
                "session_id": session_id,
                "model": model if model is not None else self.model,
                "error": str(e),
            }

    async def stream_response(
        self,
        message: str,
        session_id: str,
        system_prompt: str = None,
        api_key: str = None,
        base_url: str = None,
        model: str = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI response for a message in a session

        Args:
            message: User message
            session_id: Session identifier
            system_prompt: Optional system prompt

        Yields:
            Text chunks from the AI response
        """
        try:
            # Use custom configuration if provided, otherwise use instance configuration
            use_llm = self.llm
            if api_key is not None or base_url is not None or model is not None:
                # Create a temporary LLM with custom configuration and streaming enabled
                from langchain_openai import ChatOpenAI
                use_llm = ChatOpenAI(
                    api_key=api_key if api_key is not None else self.api_key,
                    base_url=base_url if base_url is not None else self.base_url,
                    model=model if model is not None else self.model,
                    temperature=0.7,
                    max_tokens=512,
                    streaming=True,
                )
                logger.debug(f"Using custom streaming LLM configuration: {model or self.model}")
            else:
                # Use instance LLM with streaming enabled
                # Create a new instance with streaming enabled
                from langchain_openai import ChatOpenAI
                use_llm = ChatOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model=self.model,
                    temperature=0.7,
                    max_tokens=512,
                    streaming=True,
                )

            # Get session memory
            memory = self.get_memory(session_id)

            # Prepare messages
            messages = []

            # Add system prompt if provided
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))

            # Add conversation history
            chat_history = memory.messages
            messages.extend(chat_history)

            # Add current user message
            messages.append(HumanMessage(content=message))

            # Stream response from LLM
            logger.debug(f"Streaming from LLM with {len(messages)} messages for session {session_id}")
            full_response = ""

            async for chunk in use_llm.astream(messages):
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    content = chunk.content
                    full_response += content
                    yield content

            # Save conversation to memory
            memory.add_message(HumanMessage(content=message))
            memory.add_message(AIMessage(content=full_response))

            logger.info(f"Streamed response for session {session_id}, length: {len(full_response)}")

        except Exception as e:
            logger.error(f"Error streaming response for session {session_id}: {e}")
            # Yield error message as a single chunk
            error_msg = f"\n\nI apologize, but I encountered an error: {str(e)}. Please try again."
            yield error_msg

    def switch_model(self, new_model: str, base_url: str = None, api_key: str = None):
        """Switch to a different model or API endpoint"""
        try:
            old_model = self.model
            if base_url:
                self.base_url = base_url
            if api_key:
                self.api_key = api_key

            self.model = new_model
            self._init_llm()

            logger.info(f"Switched model from {old_model} to {new_model}")
            return True
        except Exception as e:
            logger.error(f"Failed to switch model to {new_model}: {e}")
            # Revert to previous model
            self.model = old_model
            self._init_llm()
            return False

    def get_available_models(self) -> List[str]:
        """Get list of available models - returns empty list, user inputs custom model"""
        # User defines their own model name via API configuration
        # Return current model if set
        if self.model:
            return [self.model]
        return []

    def clear_memory(self, session_id: str = None):
        """Clear conversation memory for a session or all sessions"""
        if session_id:
            if session_id in self.memory_store:
                del self.memory_store[session_id]
                logger.info(f"Cleared memory for session {session_id}")
        else:
            self.memory_store.clear()
            logger.info("Cleared all conversation memory")

    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a session"""
        memory = self.get_memory(session_id)
        chat_history = memory.messages

        formatted_history = []
        for msg in chat_history:
            if isinstance(msg, HumanMessage):
                formatted_history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted_history.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                formatted_history.append({"role": "system", "content": msg.content})

        return formatted_history

# Global chat handler instance
chat_handler = ChatHandler()