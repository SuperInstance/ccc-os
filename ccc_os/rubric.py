"""CCC Decision Rubric — Enhanced with weighted scoring and confidence levels.

Determines: TELL_NOW vs LOG vs ACT vs IGNORE
Supports weighted scoring, confidence levels, and learning mode.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

Decision = Literal["TELL_NOW", "LOG", "ACT", "IGNORE"]


class Confidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Input:
    """Rubric input describing a fleet event or observation."""
    source: str  # "discussion5", "health_check", "zc_feed", "breeder_monitor", etc.
    title: str
    body: str = ""
    author: str | None = None
    has_numbers: bool = False
    is_blocker: bool = False
    affects_repos: int = 0
    asks_for_casey: bool = False
    is_breakthrough: bool = False
    is_architecture: bool = False
    is_routine_status: bool = False
    # New fields
    is_constraint_violation: bool = False
    is_anti_music: bool = False
    innovation_cycle: bool = False
    tags: list[str] = field(default_factory=list)


@dataclass
class RubricResult:
    """Result of a rubric decision with scoring details."""
    decision: Decision
    confidence: Confidence
    score: float
    matched_rule: str
    explanation: str


# Default weights (can be overridden via config)
DEFAULT_WEIGHTS = {
    "blocker": 10.0,
    "breakthrough": 8.0,
    "architecture": 6.0,
    "numbers": 5.0,
    "routine": 0.5,
    "constraint_violation": 7.0,
    "anti_music": 9.0,
    "innovation_cycle": 4.0,
}


class Rule:
    """A single rubric rule with predicate, decision, weight, and label."""

    def __init__(
        self,
        predicate,
        decision: Decision,
        weight: float,
        label: str,
        confidence: Confidence = Confidence.HIGH,
    ):
        self.predicate = predicate
        self.decision = decision
        self.weight = weight
        self.label = label
        self.confidence = confidence

    def matches(self, inp: Input) -> bool:
        try:
            return self.predicate(inp)
        except Exception:
            return False


class Rubric:
    """Enhanced decision rubric with weighted scoring."""

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.rules: list[Rule] = []
        self._decision_log: list[dict] = []
        self._build_default_rules()

    def _build_default_rules(self):
        w = self.weights
        self.rules = [
            Rule(
                lambda i: i.is_blocker,
                "TELL_NOW", w.get("blocker", 10.0),
                "blocker", Confidence.HIGH,
            ),
            Rule(
                lambda i: i.is_breakthrough,
                "TELL_NOW", w.get("breakthrough", 8.0),
                "breakthrough", Confidence.HIGH,
            ),
            Rule(
                lambda i: i.is_anti_music,
                "TELL_NOW", w.get("anti_music", 9.0),
                "anti_music", Confidence.HIGH,
            ),
            Rule(
                lambda i: i.is_constraint_violation,
                "TELL_NOW", w.get("constraint_violation", 7.0),
                "constraint_violation", Confidence.HIGH,
            ),
            Rule(
                lambda i: i.is_architecture and i.affects_repos >= 2,
                "TELL_NOW", w.get("architecture", 6.0),
                "architecture_multi_repo", Confidence.HIGH,
            ),
            Rule(
                lambda i: i.asks_for_casey,
                "TELL_NOW", 5.0,
                "asks_for_casey", Confidence.MEDIUM,
            ),
            Rule(
                lambda i: i.has_numbers and i.source == "discussion5",
                "TELL_NOW", w.get("numbers", 5.0),
                "benchmark_numbers", Confidence.MEDIUM,
            ),
            Rule(
                lambda i: i.innovation_cycle,
                "LOG", w.get("innovation_cycle", 4.0),
                "innovation_cycle", Confidence.MEDIUM,
            ),
            Rule(
                lambda i: i.is_architecture,
                "LOG", w.get("architecture", 6.0) * 0.5,
                "architecture_limited", Confidence.MEDIUM,
            ),
            Rule(
                lambda i: i.is_routine_status,
                "IGNORE", w.get("routine", 0.5),
                "routine_status", Confidence.HIGH,
            ),
            Rule(
                lambda i: i.source == "discussion5"
                and "oracle1" in i.body.lower()
                and "?" in i.body,
                "LOG", 1.0,
                "tech_question_fm_oracle", Confidence.LOW,
            ),
            Rule(
                lambda i: i.source == "zc_feed",
                "LOG", 1.5,
                "zc_feed_default", Confidence.MEDIUM,
            ),
            Rule(
                lambda i: i.source == "health_check",
                "IGNORE", 0.5,
                "health_check_default", Confidence.HIGH,
            ),
            # Catch-all
            Rule(
                lambda _: True,
                "LOG", 1.0,
                "default", Confidence.LOW,
            ),
        ]

    def decide(self, inp: Input) -> Decision:
        """Simple first-match decision (backward compatible)."""
        for rule in self.rules:
            if rule.matches(inp):
                return rule.decision
        return "LOG"

    def score(self, inp: Input) -> RubricResult:
        """Full weighted scoring with confidence."""
        best_rule: Rule | None = None
        best_score = -1.0
        all_matches: list[tuple[Rule, float]] = []

        # Evaluate all real rules first, skip the catch-all for match counting
        for rule in self.rules[:-1]:  # exclude default/catch-all
            if rule.matches(inp):
                all_matches.append((rule, rule.weight))
                if rule.weight > best_score:
                    best_score = rule.weight
                    best_rule = rule

        # Use catch-all only if nothing else matched
        if best_rule is None:
            best_rule = self.rules[-1]
            best_score = 0.0

        # Determine confidence based on match count and score
        if len(all_matches) == 1:
            confidence = best_rule.confidence
        elif len(all_matches) >= 3:
            confidence = Confidence.HIGH
        else:
            confidence = Confidence.MEDIUM

        explanation = self._explain(inp, best_rule)

        result = RubricResult(
            decision=best_rule.decision,
            confidence=confidence,
            score=best_score,
            matched_rule=best_rule.label,
            explanation=explanation,
        )

        # Log for learning mode
        self._decision_log.append({
            "input_title": inp.title,
            "input_source": inp.source,
            "decision": result.decision,
            "score": result.score,
            "confidence": result.confidence.value,
            "matched_rule": result.matched_rule,
        })

        return result

    def _explain(self, inp: Input, rule: Rule) -> str:
        reasons = []
        if inp.is_blocker:
            reasons.append("is a blocker")
        if inp.is_breakthrough:
            reasons.append("is a breakthrough")
        if inp.is_anti_music:
            reasons.append("anti-music detected")
        if inp.is_constraint_violation:
            reasons.append("constraint violation")
        if inp.is_architecture and inp.affects_repos >= 2:
            reasons.append(f"architecture affecting {inp.affects_repos} repos")
        if inp.asks_for_casey:
            reasons.append("asks for Casey")
        if inp.has_numbers and inp.source == "discussion5":
            reasons.append("has benchmark numbers")
        if inp.is_routine_status:
            reasons.append("routine status")
        if inp.innovation_cycle:
            reasons.append("innovation cycle event")
        if not reasons:
            reasons.append(f"rule: {rule.label}")

        return f"{rule.decision} — because: {', '.join(reasons)}"

    def explain(self, inp: Input) -> str:
        """Human-readable explanation (backward compat)."""
        for rule in self.rules:
            if rule.matches(inp):
                return self._explain(inp, rule)
        return "LOG — default"

    def get_decision_log(self) -> list[dict]:
        """Return accumulated decision log for learning analysis."""
        return self._decision_log.copy()

    def export_log(self, path: Path) -> None:
        """Export decision log to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self._decision_log, f, indent=2)

    def import_log(self, path: Path) -> int:
        """Import decision log from JSON file. Returns count of loaded entries."""
        if not path.exists():
            return 0
        with open(path) as f:
            entries = json.load(f)
        if isinstance(entries, list):
            self._decision_log.extend(entries)
            return len(entries)
        return 0


# Module-level convenience functions (backward compatible)
_default_rubric = Rubric()


def decide(inp: Input) -> Decision:
    """Decide using the default rubric."""
    return _default_rubric.decide(inp)


def explain(inp: Input) -> str:
    """Explain decision using the default rubric."""
    return _default_rubric.explain(inp)


def score(inp: Input) -> RubricResult:
    """Score input using the default rubric."""
    return _default_rubric.score(inp)
