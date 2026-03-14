"""Agent package exports for VeritasAI backend."""

from .claim_analyzer import analyze_claim
from .prosecutor import prosecute, run_prosecutor
from .defender import defend, run_defender
from .judge import judge, run_judge

__all__ = [
	"analyze_claim",
	"prosecute",
	"run_prosecutor",
	"defend",
	"run_defender",
	"judge",
	"run_judge",
]
