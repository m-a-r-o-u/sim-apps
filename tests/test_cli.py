from __future__ import annotations

from sim_apps.cli import main
from sim_apps.sim_integration import SIMClientAdapter


class FakeSimClient:
    def list_groups(self, service: str):
        return [
            {"id": "1", "name": "alpha"},
            {"id": "2", "name": "alpha-ai-c"},
        ]

    def list_group_members(self, group: str):
        if group in {"alpha", "1"}:
            return [
                {"personId": "p1", "primaryEmail": "alice@example.com", "emails": ["alice@example.com", "alice.smith@institution.de"]},
            ]
        return []

    def get_group_members(self, group: str):
        return self.list_group_members(group)

    def get_user(self, person_id: str):
        return {
            "personId": person_id,
            "firstName": "Alice",
            "lastName": "Smith",
            "emails": ["alice.smith@institution.de"],
        }


def test_cli_email_list_dry_run(monkeypatch, capsys) -> None:
    monkeypatch.setattr(SIMClientAdapter, "from_default", classmethod(lambda cls: SIMClientAdapter(client=FakeSimClient())))
    exit_code = main([
        "--log-level",
        "ERROR",
        "email-list",
        "--service",
        "AI",
        "--project-groups-only",
        "--with-ai-c",
        "--dedup",
        "by-best-email",
        "--institution",
        "institution",
        "--domain-hint",
        "institution.de",
        "--dry-run",
        "--stdout",
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Dry run preview" in captured.out
    assert "alice.smith@institution.de" in captured.out
