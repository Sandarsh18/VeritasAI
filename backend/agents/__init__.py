"""Agent package exports for VeritasAI backend."""

from .claim_analyzer import analyze_claim, suggest_factual_claim
from .prosecutor import run_prosecutor
from .defender import run_defender
from .judge import run_judge

__all__ = [
	"analyze_claim",
	"suggest_factual_claim",
	"run_prosecutor",
	"run_defender",
	"run_judge",
]
