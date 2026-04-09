"""Scoring rules module"""
from .research_rules import ResearchScoringRules
from .methodology_rules import MethodologyScoringRules
from .results_rules import ResultsScoringRules
from .innovation_rules import InnovationScoringRules
from .writing_rules import WritingScoringRules
from .literature_review_rules import LiteratureReviewScoringRules
from .conclusion_rules import ConclusionScoringRules

__all__ = [
    'ResearchScoringRules',
    'MethodologyScoringRules',
    'ResultsScoringRules',
    'InnovationScoringRules',
    'WritingScoringRules',
    'LiteratureReviewScoringRules',
    'ConclusionScoringRules'
]
