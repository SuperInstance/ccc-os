"""Tests for ccc_os.deck module."""

import json
from datetime import datetime, timezone

import pytest

from ccc_os.deck import Deck, Slide, benchmark_finding, architecture_decision, fleet_status, research_summary, constraint_alert


class TestSlide:
    """Test Slide dataclass."""

    def test_basic_slide(self):
        s = Slide(title="Test", bullets=["a", "b"])
        assert s.title == "Test"
        assert s.bullets == ["a", "b"]
        assert s.quote is None

    def test_slide_with_quote(self):
        s = Slide(title="Q", bullets=["x"], quote="wisdom")
        assert s.quote == "wisdom"


class TestDeck:
    """Test Deck class."""

    def test_empty_deck_render(self):
        d = Deck("My Deck", "test_type")
        rendered = d.render()
        assert "# My Deck" in rendered
        assert "test_type" in rendered
        # No slide content beyond header
        assert "## Slide" not in rendered

    def test_add_slide(self):
        d = Deck("T", "t")
        d.add(Slide("S1", ["bullet1", "bullet2"]))
        assert len(d.slides) == 1
        rendered = d.render()
        assert "## Slide 1: S1" in rendered
        assert "- bullet1" in rendered
        assert "- bullet2" in rendered

    def test_multiple_slides(self):
        d = Deck("T", "t")
        d.add(Slide("First", ["a"]))
        d.add(Slide("Second", ["b", "c"]))
        assert len(d.slides) == 2
        rendered = d.render()
        assert "## Slide 1: First" in rendered
        assert "## Slide 2: Second" in rendered

    def test_slide_with_quote_rendered(self):
        d = Deck("T", "t")
        d.add(Slide("With Quote", ["x"], quote="deep thought"))
        rendered = d.render()
        assert "> deep thought" in rendered

    def test_to_dict(self):
        d = Deck("Title", "dtype")
        d.add(Slide("S1", ["b1"], quote="q1"))
        result = d.to_dict()
        assert result["title"] == "Title"
        assert result["deck_type"] == "dtype"
        assert len(result["slides"]) == 1
        assert result["slides"][0]["title"] == "S1"
        assert result["slides"][0]["bullets"] == ["b1"]
        assert result["slides"][0]["quote"] == "q1"
        assert "generated_at" in result["meta"]
        assert result["meta"]["template"] == "dtype"

    def test_meta_fields(self):
        d = Deck("T", "t")
        assert d.meta["generated_by"] == "ccc-deck-system"
        assert d.meta["template"] == "t"


class TestTemplates:
    """Test template functions."""

    def test_benchmark_finding(self):
        result = benchmark_finding(
            "GPU Bench", "context here", "99%", "big deal", "do X", "next step",
        )
        assert "# GPU Bench" in result
        assert "## Slide 1: Context" in result
        assert "## Slide 5: Next" in result
        assert "- context here" in result

    def test_architecture_decision(self):
        result = architecture_decision(
            "AD: DB Choice", "prob", "opts", "rec", "risk", "timeline",
        )
        assert "# AD: DB Choice" in result
        assert "architecture_decision" in result
        assert "## Slide 1: The Problem" in result
        assert "## Slide 5: Timeline" in result

    def test_fleet_status_all_up(self):
        result = fleet_status(up_count=5, down_count=0, new_tiles=3, blockers=[])
        assert "5/5 UP" in result
        assert "All services operational" in result
        assert "3 new tiles this cycle" in result
        assert "None." in result

    def test_fleet_status_with_down(self):
        result = fleet_status(up_count=4, down_count=2, new_tiles=1, blockers=["DB slow", "API 500"])
        assert "4/6 UP" in result
        assert "2 DOWN" in result
        assert "- DB slow" in result
        assert "- API 500" in result

    def test_research_summary(self):
        result = research_summary("RS: LLM Scaling", "learned X", "matters Y", "do Z")
        assert "# RS: LLM Scaling" in result
        assert "research_summary" in result
        assert "- learned X" in result
        assert "- matters Y" in result
        assert "- do Z" in result

    def test_constraint_alert(self):
        result = constraint_alert("CA: Budget", "violated budget", "impact X", "fix it", "proof here")
        assert "# CA: Budget" in result
        assert "constraint_alert" in result
        assert "- violated budget" in result
        assert "- proof here" in result
        assert "- impact X" in result
        assert "- fix it" in result
