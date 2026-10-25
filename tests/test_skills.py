"""Tests for backend/skills.py (SKILL.md loader)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.skills import Skill, SkillNotFoundError, list_skills, load_skill

EXPECTED_AGENTS = [
    "boss-coordinator",
    "motor-worker",
    "language-worker",
    "social-emotional-worker",
    "cognition-worker",
    "vision-hearing-worker",
    "growth-worker",
    "school-age-behavior-worker",
    "screening-report",
    "safety-reviewer",
]


def test_list_skills_finds_all_nine_agents():
    assert sorted(list_skills()) == sorted(EXPECTED_AGENTS)


@pytest.mark.parametrize("agent_name", EXPECTED_AGENTS)
def test_each_skill_loads_with_name_description_and_instructions(agent_name):
    skill = load_skill(agent_name)
    assert isinstance(skill, Skill)
    assert skill.name == agent_name
    assert len(skill.description) > 0
    assert len(skill.instructions) > 0


def test_missing_skill_raises_skill_not_found_error():
    with pytest.raises(SkillNotFoundError):
        load_skill("does-not-exist")
