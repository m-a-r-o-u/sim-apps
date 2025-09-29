from __future__ import annotations

from pathlib import Path

from sim_apps.filters.group_filters import only_project_groups
from sim_apps.pipelines.email_list import EmailListPipeline
from sim_apps.sim_integration import SIMClientAdapter


class FakeSimClient:
    def list_groups(self, service: str):
        assert service == "AI"
        return [
            {"id": "1", "name": "alpha"},
            {"id": "2", "name": "alpha-ai-c"},
        ]

    def list_group_members(self, group: str):
        if group in {"alpha", "1"}:
            return [
                {"personId": "p1", "primaryEmail": "alice@example.com", "emails": ["alice@example.com"]},
                {"personId": "p2", "primaryEmail": "bob@example.com", "emails": ["bob@example.com"]},
            ]
        return []

    def get_group_members(self, group: str):
        return self.list_group_members(group)

    def get_user(self, person_id: str):
        return {
            "personId": person_id,
            "firstName": "Alice" if person_id == "p1" else "Bob",
            "lastName": "Smith" if person_id == "p1" else "Jones",
            "emails": [
                "alice.smith@institution.de" if person_id == "p1" else "bob.jones@institution.de"
            ],
        }


def test_email_list_pipeline(tmp_path: Path) -> None:
    client = SIMClientAdapter(client=FakeSimClient())
    output_path = tmp_path / "emails.txt"
    csv_path = tmp_path / "emails.csv"
    pipeline = EmailListPipeline(
        client=client,
        service="AI",
        group_filters=[only_project_groups()],
        dedup_strategy="by-best-email",
        institution="institution",
        domain_hint="institution.de",
        output_path=output_path,
        csv_path=csv_path,
        emit_stdout=False,
    )
    context = pipeline.run(dry_run=False)
    result = context["result"]
    assert output_path.exists()
    assert csv_path.exists()
    assert result.preview["groups_before"] == 2
    assert result.preview["groups_after"] == 1
    assert result.preview["unique_members"] == 2
    emails = output_path.read_text().split("; ")
    assert any(email.endswith("@institution.de") for email in emails)


class DuplicateEmailClient:
    def list_groups(self, service: str):
        assert service == "AI"
        return [
            {"id": "1", "name": "alpha"},
        ]

    def list_group_members(self, group: str):
        return [
            {"personId": "p1", "primaryEmail": "dup@example.com", "emails": ["dup@example.com"]},
            {"personId": "p2", "primaryEmail": "dup@example.com", "emails": ["dup@example.com"]},
        ]

    def get_group_members(self, group: str):
        return self.list_group_members(group)

    def get_user(self, person_id: str):
        return {
            "personId": person_id,
            "firstName": "Test",
            "lastName": "User",
            "emails": ["dup@example.com"],
        }


def test_email_list_pipeline_unique_emails(tmp_path: Path) -> None:
    client = SIMClientAdapter(client=DuplicateEmailClient())
    output_path = tmp_path / "emails.txt"
    pipeline = EmailListPipeline(
        client=client,
        service="AI",
        group_filters=[only_project_groups()],
        dedup_strategy="none",
        institution=None,
        domain_hint=None,
        output_path=output_path,
        csv_path=None,
        emit_stdout=False,
        unique_emails=True,
    )
    context = pipeline.run(dry_run=False)
    assert output_path.exists()
    email_list = output_path.read_text()
    assert email_list == "dup@example.com"
    assert context["email_list"] == "dup@example.com"
