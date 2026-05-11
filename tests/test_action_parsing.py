"""Smoke tests that don't require a browser or API key."""

from __future__ import annotations

import json

import pytest

from surf_agent.actions import AgentStep, ClickAction, DoneAction, TypeAction
from surf_agent.providers.base import parse_step


def test_parse_click():
    raw = json.dumps({"thought": "click the login button", "action": {"type": "click", "target_id": 3}})
    step = parse_step(raw)
    assert isinstance(step.action, ClickAction)
    assert step.action.target_id == 3


def test_parse_type_with_submit():
    raw = json.dumps(
        {
            "thought": "search for cats",
            "action": {"type": "type", "target_id": 0, "text": "cats", "submit": True},
        }
    )
    step = parse_step(raw)
    assert isinstance(step.action, TypeAction)
    assert step.action.text == "cats"
    assert step.action.submit is True


def test_parse_fenced_json():
    raw = """```json
    {"thought": "all done", "action": {"type": "done", "answer": "the answer is 42"}}
    ```"""
    step = parse_step(raw)
    assert isinstance(step.action, DoneAction)
    assert "42" in step.action.answer


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError):
        parse_step("not json at all")


def test_parse_unknown_action_raises():
    raw = json.dumps({"thought": "hmm", "action": {"type": "fly", "speed": "warp"}})
    with pytest.raises(ValueError):
        parse_step(raw)


def test_agent_step_round_trip():
    step = AgentStep(thought="x", action=DoneAction(answer="hi"))
    dumped = step.model_dump_json()
    again = AgentStep.model_validate_json(dumped)
    assert isinstance(again.action, DoneAction)
