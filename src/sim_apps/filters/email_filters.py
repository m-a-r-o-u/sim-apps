"""Email selection utilities."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable, Sequence

from ..sim_integration import Member, User


@dataclass(slots=True)
class EmailSelection:
    """Result of choosing an email for a member."""

    selected_email: str | None
    reason: str
    candidates: Sequence[str]


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).lower()


def _expected_local_part(member: Member, user: User | None) -> str | None:
    if user and user.first_name and user.last_name:
        return f"{_normalize(user.first_name)}.{_normalize(user.last_name)}"
    if member.display_name:
        tokens = [token for token in _normalize(member.display_name).replace("-", " ").split() if token]
        if len(tokens) >= 2:
            return f"{tokens[0]}.{tokens[-1]}"
    if user and user.display_name:
        tokens = [token for token in _normalize(user.display_name).replace("-", " ").split() if token]
        if len(tokens) >= 2:
            return f"{tokens[0]}.{tokens[-1]}"
    return None


def _candidate_emails(member: Member, user: User | None) -> list[str]:
    emails: list[str] = []
    for collection in (member.emails, user.emails if user else ()):  # type: ignore[arg-type]
        for email in collection or ():
            if isinstance(email, str):
                normalized = email.strip()
                if normalized and normalized not in emails:
                    emails.append(normalized)
    if member.primary_email and member.primary_email not in emails:
        emails.append(member.primary_email)
    return emails


def _local_part(email: str) -> str:
    return email.split("@", 1)[0]


def _domain_part(email: str) -> str:
    return email.split("@", 1)[1] if "@" in email else ""


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def select_best_email(
    member: Member,
    user: User | None,
    *,
    institution: str | None = None,
    domain_hint: str | None = None,
) -> EmailSelection:
    """Select the best email candidate for ``member``."""

    candidates = _candidate_emails(member, user)
    if not candidates:
        return EmailSelection(selected_email=None, reason="no candidates", candidates=())

    expected_local = _expected_local_part(member, user)
    scores: list[tuple[float, str, str]] = []
    for email in candidates:
        local = _normalize(_local_part(email))
        domain = _normalize(_domain_part(email))
        local_score = _ratio(local, expected_local) if expected_local else 0.0
        domain_score = 0.0
        if domain_hint:
            domain_score = 1.0 if domain == _normalize(domain_hint) else 0.0
        elif institution:
            if institution in domain:
                domain_score = 0.75
        total_score = 0.7 * local_score + 0.3 * domain_score
        scores.append((total_score, email, f"local={local_score:.2f},domain={domain_score:.2f}"))

    scores.sort(key=lambda item: (item[0], item[1]))
    best_score, best_email, detail = scores[-1]
    reason = f"score={best_score:.2f} ({detail})"
    return EmailSelection(selected_email=best_email, reason=reason, candidates=tuple(candidates))


__all__ = ["EmailSelection", "select_best_email"]
