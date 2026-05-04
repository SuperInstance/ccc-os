#!/usr/bin/env python3
"""
Deck Template System — Fill-in-the-blank presentation decks.
Target: <2 minutes from data to Markdown deck.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timezone

@dataclass
class Slide:
    title: str
    bullets: List[str]
    quote: Optional[str] = None

class Deck:
    def __init__(self, title: str, deck_type: str):
        self.title = title
        self.deck_type = deck_type
        self.slides = []
        self.meta = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": "ccc-deck-system",
            "template": deck_type,
        }

    def add(self, slide: Slide):
        self.slides.append(slide)

    def render(self) -> str:
        lines = [
            f"# {self.title}",
            f"_Type: {self.deck_type} | Generated: {self.meta['generated_at'][:16]}_",
            "",
            "---",
            "",
        ]
        for i, slide in enumerate(self.slides, 1):
            lines.append(f"## Slide {i}: {slide.title}")
            lines.append("")
            for b in slide.bullets:
                lines.append(f"- {b}")
            if slide.quote:
                lines.append("")
                lines.append(f"> {slide.quote}")
            lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════════════════

def benchmark_finding(title: str, context: str, numbers: str, implication: str, action: str, next_step: str) -> str:
    """Template: New benchmark finding."""
    deck = Deck(title, "benchmark_finding")
    deck.add(Slide("Context", [context]))
    deck.add(Slide("The Numbers", [numbers]))
    deck.add(Slide("What This Means", [implication]))
    deck.add(Slide("What We Should Do", [action]))
    deck.add(Slide("Next", [next_step]))
    return deck.render()

def architecture_decision(title: str, problem: str, options: str, recommendation: str, risk: str, timeline: str) -> str:
    """Template: Architecture decision deck."""
    deck = Deck(title, "architecture_decision")
    deck.add(Slide("The Problem", [problem]))
    deck.add(Slide("Options", [options]))
    deck.add(Slide("Recommendation", [recommendation]))
    deck.add(Slide("Risk", [risk]))
    deck.add(Slide("Timeline", [timeline]))
    return deck.render()

def fleet_status(up_count: int, down_count: int, new_tiles: int, blockers: List[str]) -> str:
    """Template: Fleet status snapshot."""
    deck = Deck("Fleet Status", "fleet_status")
    total = up_count + down_count
    deck.add(Slide("Services", [
        f"{up_count}/{total} UP",
        f"{down_count} DOWN" if down_count else "All services operational",
    ]))
    deck.add(Slide("PLATO", [
        f"{new_tiles} new tiles this cycle",
    ]))
    if blockers:
        deck.add(Slide("Blockers", blockers))
    else:
        deck.add(Slide("Blockers", ["None."]))
    return deck.render()

def research_summary(title: str, what_learned: str, why_matters: str, what_to_do: str) -> str:
    """Template: Research summary."""
    deck = Deck(title, "research_summary")
    deck.add(Slide("What We Learned", [what_learned]))
    deck.add(Slide("Why It Matters", [why_matters]))
    deck.add(Slide("What To Do", [what_to_do]))
    return deck.render()

# ═══════════════════════════════════════════════════════════════════
# TEST / DEMONSTRATION
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Demo: The CPU Breakthrough deck
    print(benchmark_finding(
        title="CPU Beats GPU: The AVX-512 Finding",
        context="FM ran head-to-head AVX-512 vs RTX 4050 on constraint checking",
        numbers="""CPU (Ryzen AI 9): 5.7B checks/s
GPU (RTX 4050): 1.03B checks/s
Advantage: 5.5x faster on CPU
20 constraints in parallel: 35.9B/s via AND-logic""",
        implication="FLUX-C (constraint layer) should compile to AVX-512, not CUDA. The bridge to FLUX-X has a physical reason: register file vs VRAM.",
        action="Buy Ryzen AI 9s with AVX-512 for constraint screening. Reserve GPUs for complex FLUX-X ops only.",
        next_step="Oracle1 to add Section 13 to ISA v3 documenting bare-metal compilation targets. FM to build flux-cpu-avx512 repo.",
    ))
