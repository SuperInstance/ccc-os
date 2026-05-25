"""Tests for ccc_os.rubric module."""

import pytest
from ccc_os.rubric import Input, Rubric, decide, explain, score, Confidence


class TestDecide:
    """Test basic first-match decision logic."""

    def test_blocker(self):
        inp = Input("test", "Blocker", is_blocker=True)
        assert decide(inp) == "TELL_NOW"

    def test_breakthrough(self):
        inp = Input("test", "Breakthrough", is_breakthrough=True)
        assert decide(inp) == "TELL_NOW"

    def test_anti_music(self):
        inp = Input("test", "Anti-music", is_anti_music=True)
        assert decide(inp) == "TELL_NOW"

    def test_constraint_violation(self):
        inp = Input("test", "Constraint violation", is_constraint_violation=True)
        assert decide(inp) == "TELL_NOW"

    def test_architecture_multi_repo(self):
        inp = Input("test", "Architecture", is_architecture=True, affects_repos=3)
        assert decide(inp) == "TELL_NOW"

    def test_asks_for_casey(self):
        inp = Input("test", "Casey needed", asks_for_casey=True)
        assert decide(inp) == "TELL_NOW"

    def test_benchmark_numbers(self):
        inp = Input("discussion5", "Benchmark", has_numbers=True)
        assert decide(inp) == "TELL_NOW"

    def test_routine_status(self):
        inp = Input("test", "Routine", is_routine_status=True)
        assert decide(inp) == "IGNORE"

    def test_zc_feed_default(self):
        inp = Input("zc_feed", "New tile")
        assert decide(inp) == "LOG"

    def test_health_check_default(self):
        inp = Input("health_check", "All OK")
        assert decide(inp) == "IGNORE"

    def test_default_log(self):
        inp = Input("unknown", "Something", body="random text")
        assert decide(inp) == "LOG"


class TestExplain:
    """Test explanation strings."""

    def test_blocker_explanation(self):
        inp = Input("test", "Blocker", is_blocker=True)
        exp = explain(inp)
        assert "TELL_NOW" in exp
        assert "blocker" in exp.lower()

    def test_routine_explanation(self):
        inp = Input("test", "Routine", is_routine_status=True)
        exp = explain(inp)
        assert "IGNORE" in exp


class TestRubric:
    """Test the Rubric class with weighted scoring."""

    def test_score_blocker(self):
        rubric = Rubric()
        inp = Input("test", "Blocker", is_blocker=True)
        result = rubric.score(inp)
        assert result.decision == "TELL_NOW"
        assert result.score == 10.0
        assert result.confidence == Confidence.HIGH

    def test_score_breakthrough(self):
        rubric = Rubric()
        inp = Input("test", "Breakthrough", is_breakthrough=True)
        result = rubric.score(inp)
        assert result.decision == "TELL_NOW"
        assert result.score == 8.0

    def test_custom_weights(self):
        rubric = Rubric(weights={"blocker": 99.0, "breakthrough": 1.0, "routine": 0.5})
        inp = Input("test", "Blocker", is_blocker=True)
        result = rubric.score(inp)
        assert result.score == 99.0

    def test_decision_log(self):
        rubric = Rubric()
        rubric.score(Input("test", "A", is_blocker=True))
        rubric.score(Input("test", "B", is_routine_status=True))
        log = rubric.get_decision_log()
        assert len(log) == 2
        assert log[0]["decision"] == "TELL_NOW"
        assert log[1]["decision"] == "IGNORE"

    def test_export_import_log(self, tmp_path):
        rubric = Rubric()
        rubric.score(Input("test", "A", is_blocker=True))
        log_path = tmp_path / "log.json"
        rubric.export_log(log_path)

        rubric2 = Rubric()
        count = rubric2.import_log(log_path)
        assert count == 1
        assert len(rubric2.get_decision_log()) == 1

    def test_import_nonexistent(self, tmp_path):
        rubric = Rubric()
        count = rubric.import_log(tmp_path / "nonexistent.json")
        assert count == 0

    def test_multiple_matches_higher_confidence(self):
        rubric = Rubric()
        # This input matches multiple rules
        inp = Input("test", "Multi", is_blocker=True, is_breakthrough=True, is_anti_music=True)
        result = rubric.score(inp)
        assert result.confidence == Confidence.HIGH  # 3+ matches
        assert result.decision == "TELL_NOW"
