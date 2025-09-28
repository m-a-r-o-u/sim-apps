"""Filters for SIM group member collections."""

from __future__ import annotations

from typing import Callable, Iterable

from ..sim_integration import Member

DedupStrategy = str


def deduplicate_members(strategy: DedupStrategy) -> Callable[[Iterable[Member]], list[Member]]:
    """Return a filter that deduplicates members according to ``strategy``."""

    normalized = strategy.lower()
    if normalized not in {"none", "by-id", "by-primary-email", "by-best-email"}:
        raise ValueError(f"Unsupported deduplication strategy: {strategy}")

    def _filter(members: Iterable[Member], /, **kwargs: object) -> list[Member]:
        if normalized == "none":
            return list(members)
        seen: set[str] = set()
        result: list[Member] = []
        for member in members:
            if normalized == "by-id":
                key = member.person_id
            elif normalized == "by-primary-email":
                key = (member.primary_email or "").lower()
            else:
                selector = kwargs.get("email_selector")
                if not callable(selector):
                    raise ValueError("email_selector callable required for by-best-email")
                selection = selector(member, **kwargs)
                key = selection.selected_email or member.person_id
            if key in seen:
                continue
            if key:
                seen.add(key)
            result.append(member)
        return result

    return _filter


__all__ = ["deduplicate_members", "DedupStrategy"]
