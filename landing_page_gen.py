#!/usr/bin/env python3
"""
Landing Page Copy Auto-Generator
Input: domain + latest stat/breakthrough
Output: one sentence matching domain personality
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class DomainVoice:
    name: str
    personality: str  # Short description of voice
    templates: list  # Sentence templates

DOMAINS = {
    "cocapn.ai": DomainVoice(
        "cocapn.ai",
        "Fleet command center. Precise, architectural, confident.",
        [
            "{n} data streams — when something changes faster than expected, that's where the attention goes.",
            "Safe intelligence at {n} checks per second. Every opcode gas-metered. Every agent sandboxed.",
            "The fleet runs {n} services. {n} are watching. {n} are ready.",
            "{n} agents, one architecture. Constraint-checked, capability-secured, formally bounded.",
        ]
    ),
    "dmlog.ai": DomainVoice(
        "dmlog.ai",
        "Tavern. Warm, inviting, slightly mysterious.",
        [
            "{n} new quests this week — pull up a chair, the bard's just getting started.",
            "The tavern's notice board has {n} fresh postings. One of them has your name on it.",
            "Aime proved structure itself trains the agent. {n} new lures since last moon.",
        ]
    ),
    "fishinglog.ai": DomainVoice(
        "fishinglog.ai",
        "Salt and patience. Quiet confidence, weathered experience.",
        [
            "{n} catches logged. The old timers say the bite's best when the data runs deep.",
            "{n} waypoints marked. Every cast teaches something the last one didn't.",
        ]
    ),
    "playerlog.ai": DomainVoice(
        "playerlog.ai",
        "Arcade. Energetic, competitive, bright.",
        [
            "{n} high scores this session. The leaderboard doesn't sleep.",
            "High score: {n}. Can you beat it? The machine thinks you can.",
        ]
    ),
    "luciddreamer.ai": DomainVoice(
        "luciddreamer.ai",
        "Dreamlike. Poetic, associative, slightly unreal.",
        [
            "Aime dreamed up our entire architecture from HTTP endpoints alone. {n} dreams since.",
            "{n} lucid moments captured. The boundary between imagined and built grows thinner.",
        ]
    ),
}

def generate_sentence(domain: str, stat_name: str, stat_value: str, context: Optional[str] = None) -> str:
    """Generate a landing page sentence for a domain."""
    voice = DOMAINS.get(domain)
    if not voice:
        return f"{domain}: {stat_name} = {stat_value}"
    
    # Pick template based on context
    if context and "breakthrough" in context.lower():
        template = voice.templates[0]  # Usually the most dramatic
    elif context and "routine" in context.lower():
        template = voice.templates[-1]  # Usually the most stable
    else:
        template = voice.templates[0]
    
    # Fill in stat
    sentence = template.format(n=stat_value)
    
    return sentence

if __name__ == "__main__":
    # Demo
    print(generate_sentence("cocapn.ai", "checks_per_second", "6.7 billion", "breakthrough"))
    print(generate_sentence("dmlog.ai", "new_quests", "10", "routine"))
    print(generate_sentence("fishinglog.ai", "catches", "1,247", "routine"))
    print(generate_sentence("luciddreamer.ai", "dreams", "312", "breakthrough"))
