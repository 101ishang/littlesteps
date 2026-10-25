"""Load agent instructions from SKILL.md files.

Each agent in Agents.md's "Agents in this project" table has a skills/<agent-name>/SKILL.md
file: YAML frontmatter (name, description) plus a Markdown body of instructions. PydanticAI
agents are built with `instructions=load_skill("<agent-name>").instructions` rather than an
inline prompt string, so the prompt lives in a reviewable, version-controlled file (see
Agents.md -> Conventions).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


class SkillNotFoundError(FileNotFoundError):
    pass


class SkillFormatError(ValueError):
    pass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    instructions: str


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise SkillFormatError("SKILL.md must start with a '---' YAML frontmatter block")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SkillFormatError("SKILL.md frontmatter block is not closed with '---'")
    _, frontmatter_raw, body = parts
    frontmatter = yaml.safe_load(frontmatter_raw) or {}
    if not isinstance(frontmatter, dict):
        raise SkillFormatError("SKILL.md frontmatter must be a YAML mapping")
    return frontmatter, body.strip()


def load_skill(agent_name: str) -> Skill:
    """Load skills/<agent_name>/SKILL.md.

    agent_name is the kebab-case directory name, e.g. "motor-worker", "safety-reviewer".
    """
    path = SKILLS_DIR / agent_name / "SKILL.md"
    if not path.exists():
        raise SkillNotFoundError(f"No SKILL.md found for agent '{agent_name}' at {path}")

    frontmatter, body = _split_frontmatter(path.read_text(encoding="utf-8"))

    for required in ("name", "description"):
        if required not in frontmatter:
            raise SkillFormatError(f"{path} frontmatter is missing required field '{required}'")

    return Skill(name=frontmatter["name"], description=frontmatter["description"], instructions=body)


def list_skills() -> list[str]:
    """List available agent skill names (directory names under skills/)."""
    if not SKILLS_DIR.exists():
        return []
    return sorted(p.name for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "SKILL.md").exists())
