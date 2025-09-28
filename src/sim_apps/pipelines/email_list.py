"""Pipeline implementation for generating email lists."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..filters.email_filters import EmailSelection, select_best_email
from ..filters.group_filters import GroupSequence
from ..filters.member_filters import DedupStrategy, deduplicate_members
from ..sim_integration import Group, Member, SIMClientAdapter, User
from .base import Pipeline, PipelineContext, PipelineStep

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class EmailListResult:
    rows: list[dict[str, Any]]
    preview: dict[str, Any]


class EmailListPipeline(Pipeline):
    """Pipeline that produces email lists for SIM groups."""

    def __init__(
        self,
        *,
        client: SIMClientAdapter,
        service: str,
        group_filters: Sequence[Any],
        dedup_strategy: DedupStrategy,
        institution: str | None,
        domain_hint: str | None,
        output_path: Path | None,
        csv_path: Path | None,
        emit_stdout: bool,
        debug_dir: Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(name="email-list", debug_dir=debug_dir, logger=logger)
        self.client = client
        self.service = service
        self.group_filters = group_filters
        self.dedup_strategy = dedup_strategy
        self.institution = institution
        self.domain_hint = domain_hint
        self.output_path = output_path
        self.csv_path = csv_path
        self.emit_stdout = emit_stdout

        self.add_step(PipelineStep("list-groups", self._list_groups_step))
        self.add_step(PipelineStep("apply-group-filters", self._apply_group_filters_step))
        self.add_step(PipelineStep("load-members", self._load_members_step))
        self.add_step(PipelineStep("deduplicate-members", self._deduplicate_members_step))
        self.add_step(PipelineStep("load-users", self._load_users_step))
        self.add_step(PipelineStep("select-emails", self._select_emails_step))
        self.add_step(PipelineStep("write-outputs", self._write_outputs_step))

    def _list_groups_step(self, context: PipelineContext) -> PipelineContext:
        groups = self.client.list_groups(self.service)
        context["groups_before_filters"] = groups
        return context

    def _apply_group_filters_step(self, context: PipelineContext) -> PipelineContext:
        universe: GroupSequence = context.get("groups_before_filters", [])
        filtered = list(universe)
        for filt in self.group_filters:
            filtered = filt(filtered, all_groups=universe)
        context["groups"] = filtered
        return context

    def _load_members_step(self, context: PipelineContext) -> PipelineContext:
        groups: Sequence[Group] = context.get("groups", [])
        members: list[Member] = []
        membership_map: dict[str, list[Member]] = {}
        for group in groups:
            group_members = self.client.list_group_members(group)
            membership_map[group.name] = group_members
            members.extend(group_members)
        context["members"] = members
        context["membership_map"] = membership_map
        return context

    def _deduplicate_members_step(self, context: PipelineContext) -> PipelineContext:
        members: Iterable[Member] = context.get("members", [])
        dedup_filter = deduplicate_members(self.dedup_strategy)
        context["deduplicated_members"] = dedup_filter(
            members,
            email_selector=self._email_selector,
        )
        return context

    def _load_users_step(self, context: PipelineContext) -> PipelineContext:
        members: Iterable[Member] = context.get("deduplicated_members", [])
        users: dict[str, User] = {}
        for member in members:
            if member.person_id not in users:
                users[member.person_id] = self.client.get_user(member.person_id)
        context["users"] = users
        return context

    def _select_emails_step(self, context: PipelineContext) -> PipelineContext:
        members: Sequence[Member] = context.get("deduplicated_members", [])
        users: dict[str, User] = context.get("users", {})
        rows: list[dict[str, Any]] = []
        selections: dict[str, EmailSelection] = {}
        for member in members:
            selection = self._email_selector(member, user=users.get(member.person_id))
            selections[member.person_id] = selection
            rows.append(
                {
                    "group_id": member.group_id,
                    "person_id": member.person_id,
                    "display_name": member.display_name,
                    "chosen_email": selection.selected_email,
                    "all_emails": list(selection.candidates),
                    "reason": selection.reason,
                }
            )
        context["email_rows"] = rows
        context["selections"] = selections
        return context

    def _write_outputs_step(self, context: PipelineContext) -> PipelineContext:
        rows: Sequence[dict[str, Any]] = context.get("email_rows", [])
        dry_run: bool = bool(context.get("dry_run", False))
        text_rows = [row for row in rows if row.get("chosen_email")]
        email_list = "; ".join(row["chosen_email"] for row in text_rows if row.get("chosen_email"))
        context["email_list"] = email_list
        if self.emit_stdout or dry_run:
            context["stdout_output"] = email_list
        preview = self._build_preview(context)
        context["preview"] = preview
        if not dry_run:
            if self.output_path:
                self.output_path.parent.mkdir(parents=True, exist_ok=True)
                self.output_path.write_text(email_list)
            if self.csv_path:
                self.csv_path.parent.mkdir(parents=True, exist_ok=True)
                with self.csv_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(
                        handle,
                        fieldnames=[
                            "group_id",
                            "person_id",
                            "display_name",
                            "chosen_email",
                            "all_emails",
                            "reason",
                        ],
                    )
                    writer.writeheader()
                    for row in rows:
                        csv_row = dict(row)
                        csv_row["all_emails"] = ", ".join(csv_row.get("all_emails", []))
                        writer.writerow(csv_row)
        context["result"] = EmailListResult(rows=list(rows), preview=preview)
        return context

    def _email_selector(self, member: Member, **kwargs: Any) -> EmailSelection:
        user = kwargs.get("user")
        if user is not None and not isinstance(user, User):
            raise TypeError("user must be a User or None")
        return select_best_email(
            member,
            user,
            institution=self.institution,
            domain_hint=self.domain_hint,
        )

    def _build_preview(self, context: PipelineContext) -> dict[str, Any]:
        before = context.get("groups_before_filters", [])
        after = context.get("groups", [])
        members = context.get("deduplicated_members", [])
        rows: Sequence[dict[str, Any]] = context.get("email_rows", [])
        sample = rows[:10]
        return {
            "groups_before": len(before),
            "groups_after": len(after),
            "unique_members": len(list(members)),
            "sample": sample,
        }


__all__ = ["EmailListPipeline", "EmailListResult"]
