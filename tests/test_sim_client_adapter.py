from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from sim_apps.sim_integration import SIMClientAdapter


class FakeSimClient:
    def list_groups(self, service: str):
        return []

    def list_group_members(self, group: str):
        return []

    def get_user(self, person_id: str):
        return {"id": person_id}


def test_from_default_resolves_nested_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    module = SimpleNamespace(
        Client=SimpleNamespace(factory=lambda **_: FakeSimClient())
    )
    monkeypatch.setitem(sys.modules, "sim_api_wrapper", module)

    adapter = SIMClientAdapter.from_default()

    assert isinstance(adapter.client, FakeSimClient)
