"""Manage ignored entities for review system"""

import os
import logging
from typing import List, Set
from pathlib import Path

logger = logging.getLogger(__name__)

# Default path for ignored entities file
DEFAULT_IGNORED_ENTITIES_PATH = Path(__file__).parent.parent.parent / "config" / "ignored_entities.md"


class IgnoredEntitiesManager:
    """Manage list of entities to ignore in review generation"""

    def __init__(self, file_path: str = None):
        self.file_path = Path(file_path) if file_path else DEFAULT_IGNORED_ENTITIES_PATH
        self._ignored_entities: Set[str] = set()
        self._load_ignored_entities()

    def _load_ignored_entities(self) -> None:
        """Load ignored entities from file"""
        self._ignored_entities.clear()

        if not self.file_path.exists():
            logger.warning(f"Ignored entities file not found: {self.file_path}")
            return

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    # Add entity name (case-insensitive, but store as lowercase for comparison)
                    entity_name = line.lower().strip()
                    if entity_name:
                        self._ignored_entities.add(entity_name)

            logger.info(f"Loaded {len(self._ignored_entities)} ignored entities from {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to load ignored entities from {self.file_path}: {e}")
            self._ignored_entities.clear()

    def save_ignored_entities(self) -> bool:
        """Save ignored entities to file"""
        try:
            # Ensure directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write("# 屏蔽的实体列表\n")
                f.write("# 这些实体将不会出现在复习问题中\n")
                f.write("# 每行一个实体名称，不区分大小写\n")
                f.write("# 空行和以#开头的行会被忽略\n\n")

                # Write entities in alphabetical order
                for entity in sorted(self._ignored_entities):
                    f.write(f"{entity}\n")

            logger.info(f"Saved {len(self._ignored_entities)} ignored entities to {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save ignored entities to {self.file_path}: {e}")
            return False

    def is_ignored(self, entity_name: str) -> bool:
        """Check if an entity is ignored (case-insensitive)"""
        if not entity_name:
            return False
        return entity_name.lower().strip() in self._ignored_entities

    def add_ignored_entity(self, entity_name: str) -> bool:
        """Add an entity to the ignored list"""
        if not entity_name:
            return False

        entity_name = entity_name.lower().strip()
        if entity_name in self._ignored_entities:
            return True  # Already ignored

        self._ignored_entities.add(entity_name)
        return self.save_ignored_entities()

    def remove_ignored_entity(self, entity_name: str) -> bool:
        """Remove an entity from the ignored list"""
        if not entity_name:
            return False

        entity_name = entity_name.lower().strip()
        if entity_name not in self._ignored_entities:
            return True  # Not in list, nothing to remove

        self._ignored_entities.remove(entity_name)
        return self.save_ignored_entities()

    def get_ignored_entities(self) -> List[str]:
        """Get list of all ignored entities (sorted)"""
        return sorted(self._ignored_entities)

    def clear_ignored_entities(self) -> bool:
        """Clear all ignored entities"""
        self._ignored_entities.clear()
        return self.save_ignored_entities()

    def reload(self) -> None:
        """Reload ignored entities from file"""
        self._load_ignored_entities()


# Global instance
ignored_entities_manager = IgnoredEntitiesManager()


# Convenience functions
def is_entity_ignored(entity_name: str) -> bool:
    """Check if an entity is ignored (case-insensitive)"""
    return ignored_entities_manager.is_ignored(entity_name)


def get_ignored_entities_list() -> List[str]:
    """Get list of all ignored entities"""
    return ignored_entities_manager.get_ignored_entities()


def add_ignored_entity(entity_name: str) -> bool:
    """Add an entity to the ignored list"""
    return ignored_entities_manager.add_ignored_entity(entity_name)


def remove_ignored_entity(entity_name: str) -> bool:
    """Remove an entity from the ignored list"""
    return ignored_entities_manager.remove_ignored_entity(entity_name)


def clear_ignored_entities() -> bool:
    """Clear all ignored entities"""
    return ignored_entities_manager.clear_ignored_entities()