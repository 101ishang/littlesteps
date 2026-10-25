"""Structural privacy checks on the DB schema itself (backend/db.py).

These guard the design invariant described in AnalyticsEvent's docstring:
no column on that table can ever hold a user/child identifier or PII,
because the column doesn't exist — not because of an access rule.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import AnalyticsEvent, Child, User

FORBIDDEN_SUBSTRINGS = ("user", "child", "email", "name", "nickname")


def test_analytics_event_has_no_identifying_columns():
    columns = {c.name for c in AnalyticsEvent.__table__.columns}
    assert "id" in columns  # the table's own surrogate key is fine
    columns.discard("id")
    for col in columns:
        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in col.lower(), (
                f"AnalyticsEvent.{col} looks like it could identify a user or child "
                f"(matches '{forbidden}') — analytics must stay structurally anonymous."
            )


def test_analytics_event_has_no_foreign_keys():
    assert len(AnalyticsEvent.__table__.foreign_keys) == 0


def test_user_password_hash_column_is_named_explicitly_not_password():
    # Guards against ever accidentally storing/returning a plaintext "password" column.
    columns = {c.name for c in User.__table__.columns}
    assert "password_hash" in columns
    assert "password" not in columns


def test_child_belongs_to_exactly_one_user():
    fks = list(Child.__table__.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "users"
