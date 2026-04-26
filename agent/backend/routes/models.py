from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import logging

from backend.llm.chat_handler import chat_handler
from backend.llm.model_registry import model_registry

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models

class ModelInfo(BaseModel):
    name: str
    display_name: str
    provider: str
    description: str
    context_length: int
    supports_vision: bool
    default_temperature: float

class SwitchModelRequest(BaseModel):
    model_name: str
    base_url: str = None

class SwitchModelResponse(BaseModel):
    success: bool
    previous_model: str
    new_model: str
    message: str

# Routes

@router.get("/models", response_model=List[ModelInfo])
async def get_available_models():
    """
    Get list of available LLM models
    """
    try:
        logger.info("Getting available models")
        models = model_registry.get_available_models()
        return models
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/models/current", response_model=ModelInfo)
async def get_current_model():
    """Get information about the currently active model"""
    try:
        current_model = model_registry.get_active_model()
        if not current_model:
            raise HTTPException(status_code=404, detail="No active model found")
        return current_model
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current model: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/models/switch", response_model=SwitchModelResponse)
async def switch_model(request: SwitchModelRequest):
    """
    Switch to a different LLM model
    """
    try:
        logger.info(f"Switching model to: {request.model_name}")

        # Get current model
        current_model = model_registry.get_active_model()
        previous_model = current_model.get("name", "unknown")

        # Validate model exists
        model_info = model_registry.get_model(request.model_name)
        if not model_info:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{request.model_name}' not found in registry"
            )

        # Try to switch in chat handler
        success = chat_handler.switch_model(
            new_model=request.model_name,
            base_url=request.base_url
        )

        if success:
            # Update active model in registry
            model_registry.set_active_model(request.model_name)

            response_data = {
                "success": True,
                "previous_model": previous_model,
                "new_model": request.model_name,
                "message": f"Successfully switched to {request.model_name}"
            }
            logger.info(f"Model switched from {previous_model} to {request.model_name}")
            return SwitchModelResponse(**response_data)
        else:
            response_data = {
                "success": False,
                "previous_model": previous_model,
                "new_model": previous_model,  # Reverted to previous
                "message": f"Failed to switch to {request.model_name}"
            }
            return SwitchModelResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching model: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to switch model: {str(e)}"
        )

@router.get("/models/search")
async def search_models(query: str):
    """Search models by name or description"""
    try:
        logger.info(f"Searching models with query: {query}")
        if not query or len(query) < 2:
            raise HTTPException(
                status_code=400,
                detail="Search query must be at least 2 characters"
            )

        results = model_registry.search_models(query)
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching models: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/models/stats")
async def get_model_stats():
    """Get statistics about model usage"""
    try:
        # Placeholder statistics
        return {
            "total_models": len(model_registry.get_available_models()),
            "active_model": model_registry.active_model,
            "total_requests": 0,  # Would track in production
            "avg_response_time": 0,
            "success_rate": 1.0
        }
    except Exception as e:
        logger.error(f"Error getting model stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")