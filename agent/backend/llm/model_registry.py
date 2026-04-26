from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class ModelRegistry:
    """Registry for managing available LLM models and their configurations"""

    def __init__(self):
        self.models = self._load_default_models()
        self.active_model = "custom"  # Default model

    def _load_default_models(self) -> Dict[str, Dict[str, Any]]:
        """Load default model configurations - minimal preset"""
        return {
            "custom": {
                "name": "custom",
                "display_name": "Custom Model",
                "provider": "custom",
                "description": "User-defined model configuration",
                "context_length": 4096,
                "supports_vision": False,
                "default_temperature": 0.7,
            },
        }

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        return list(self.models.values())

    def get_model(self, model_name: str) -> Dict[str, Any]:
        """Get configuration for a specific model"""
        return self.models.get(model_name, {})

    def set_active_model(self, model_name: str) -> bool:
        """Set the active model"""
        if model_name in self.models:
            self.active_model = model_name
            logger.info(f"Active model changed to: {model_name}")
            return True
        else:
            logger.warning(f"Model not found: {model_name}")
            return False

    def get_active_model(self) -> Dict[str, Any]:
        """Get configuration for the active model"""
        return self.models.get(self.active_model, {})

    def add_custom_model(self, model_config: Dict[str, Any]) -> bool:
        """Add a custom model configuration"""
        model_name = model_config.get("name")
        if not model_name:
            logger.error("Custom model configuration missing 'name' field")
            return False

        self.models[model_name] = model_config
        logger.info(f"Added custom model: {model_name}")
        return True

    def remove_model(self, model_name: str) -> bool:
        """Remove a model from the registry"""
        if model_name in self.models and model_name != "custom":  # Prevent removing default
            del self.models[model_name]
            logger.info(f"Removed model: {model_name}")
            return True
        return False

    def search_models(self, query: str) -> List[Dict[str, Any]]:
        """Search models by name or description"""
        query = query.lower()
        results = []
        for model in self.models.values():
            if (query in model["name"].lower() or
                query in model["display_name"].lower() or
                query in model["description"].lower()):
                results.append(model)
        return results

# Global model registry instance
model_registry = ModelRegistry()