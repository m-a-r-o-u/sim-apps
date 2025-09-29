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

    def get_group_members(self, group: str):
        return []

    def get_user(self, person_id: str):
        return {"id": person_id}


class OnlyGetGroupMembersClient:
    def list_groups(self, service: str):
        return []

    def get_group_members(self, group: str):
        return [{"personId": "p1", "groupId": group}]

    def get_user(self, person_id: str):
        return {"id": person_id}


class NonMappingGroupClient:
    def list_groups(self, service: str):
        return [123, {"id": "good", "name": "Good"}]

    def list_group_members(self, group: str):
        return []

    def get_group_members(self, group: str):
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


def test_adapter_uses_get_group_members_when_list_missing() -> None:
    adapter = SIMClientAdapter(client=OnlyGetGroupMembersClient())

    members = adapter.list_group_members("grp")

    assert members[0].group_id == "grp"
    assert members[0].person_id == "p1"


def test_adapter_skips_non_mapping_group_payloads(caplog: pytest.LogCaptureFixture) -> None:
    adapter = SIMClientAdapter(client=NonMappingGroupClient())

    with caplog.at_level("WARNING"):
        groups = adapter.list_groups("svc")

    assert [group.id for group in groups] == ["good"]
    assert "Skipping group payload with unexpected type" in caplog.text


class StringGroupClient:
    def list_groups(self, service: str):
        return ["proj-ai-c", '{"id": "proj", "name": "Project"}']

    def list_group_members(self, group: str):
        return []

    def get_group_members(self, group: str):
        return []

    def get_user(self, person_id: str):
        return {"id": person_id}


def test_adapter_coerces_string_group_payloads(caplog: pytest.LogCaptureFixture) -> None:
    adapter = SIMClientAdapter(client=StringGroupClient())

    with caplog.at_level("WARNING"):
        groups = adapter.list_groups("svc")

    assert [group.id for group in groups] == ["proj-ai-c", "proj"]
    assert "Skipping empty group payload string" not in caplog.text
