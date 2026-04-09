"""
Configuration module for Thesis Reviewer
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: str = "anthropic"  # "anthropic" or "openai"
    model: str = "claude-sonnet-4-6-20250514"
    api_key: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.0


@dataclass
class ScoringConfig:
    """Scoring dimension weights (must sum to 100)"""
    research_question: int = 15
    methodology: int = 25
    results: int = 20
    innovation: int = 15
    structure: int = 10
    writing: int = 15


@dataclass
class ReviewerConfig:
    """Main configuration for the reviewer system"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    cite_format: str = "quote"
    debug: bool = False


DEFAULT_CONFIG = ReviewerConfig()


def load_config() -> ReviewerConfig:
    """Load configuration from environment or use defaults"""
    config = DEFAULT_CONFIG

    if os.getenv("ANTHROPIC_API_KEY"):
        config.llm.api_key = os.getenv("ANTHROPIC_API_KEY")
        config.llm.provider = "anthropic"

    if os.getenv("OPENAI_API_KEY"):
        config.llm.provider = "openai"
        config.llm.api_key = os.getenv("OPENAI_API_KEY")

    return config
