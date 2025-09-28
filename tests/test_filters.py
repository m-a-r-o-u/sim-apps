from __future__ import annotations

from sim_apps.filters.email_filters import EmailSelection, select_best_email
from sim_apps.filters.group_filters import (
    only_ai_c_groups,
    only_ai_h_mcml_groups,
    only_project_groups,
    with_ai_c_but_without_ai_h_mcml,
    with_ai_c_companion,
)
from sim_apps.sim_integration import Group, Member, User


def _make_group(name: str) -> Group:
    return Group(id=name, name=name)


def test_group_filters_project_only() -> None:
    groups = [_make_group("pr92no"), _make_group("pr92no-ai-c"), _make_group("pr92no-ai-h-mcml")]
    filtered = only_project_groups()(groups)
    assert [group.name for group in filtered] == ["pr92no"]


def test_group_filters_with_companions() -> None:
    groups = [
        _make_group("alpha"),
        _make_group("alpha-ai-c"),
        _make_group("alpha-ai-h-mcml"),
        _make_group("beta"),
        _make_group("beta-ai-c"),
    ]
    filtered = with_ai_c_companion()(groups)
    assert {group.name for group in filtered} == {"alpha", "beta"}
    filtered = with_ai_c_but_without_ai_h_mcml()(groups)
    assert [group.name for group in filtered] == ["beta"]


def test_group_filters_only_ai_variants() -> None:
    groups = [_make_group("pr92no"), _make_group("pr92no-ai-c"), _make_group("pr92no-ai-h-mcml"), _make_group("gamma-ai-c")]
    assert {group.name for group in only_ai_c_groups()(groups)} == {"pr92no-ai-c", "gamma-ai-c"}
    assert {group.name for group in only_ai_h_mcml_groups()(groups)} == {"pr92no-ai-h-mcml"}


def test_select_best_email_prefers_pattern() -> None:
    member = Member(person_id="1", group_id="g", emails=["random@example.com", "alice.smith@institution.de"], display_name="Alice Smith")
    user = User(person_id="1", first_name="Alice", last_name="Smith", display_name="Alice Smith", emails=["alias@institution.de"])
    selection = select_best_email(member, user, institution="institution", domain_hint="institution.de")
    assert isinstance(selection, EmailSelection)
    assert selection.selected_email == "alice.smith@institution.de"
    assert "score=" in selection.reason
