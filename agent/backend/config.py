import os
from dotenv import load_dotenv

load_dotenv()

# LLM Configuration
# OpenAI-compatible API configuration (defaults can be overridden by frontend)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")  # For OpenAI-compatible APIs

# Relational Database (SQLite or PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chat.db")
# Example: DATABASE_URL = "postgresql://user:pass@localhost/dbname"

# Neo4j Graph Database
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")