"""Tests for the chat app.

This directory did not exist. `apps/chat` is the only app under `apps/` with no
tests at all, and it is the one whose failure modes are the most visible: a DM
that 500s, two conversations between the same pair of people, and a room whose
name the other participant did not choose.

`conftest.py` and `factories.py` follow `apps/community/tests` and
`apps/workspaces/tests` rather than inventing a third convention.
"""
