"""Models used to normalize SIM API data for the application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, MutableMapping, Sequence, cast


def _get_value(raw: Mapping[str, object] | object, *names: str, required: bool = False):
    """Retrieve a value from ``raw`` supporting mappings and attribute access."""

    is_mapping = isinstance(raw, Mapping)
    for name in names:
        if is_mapping:
            mapping = cast(Mapping[str, object], raw)
            if name in mapping:
                return mapping[name]
        else:
            if hasattr(raw, name):
                return getattr(raw, name)
    if required:
        raise KeyError(names[0])
    return None


@dataclass(slots=True)
class Group:
    """Representation of a SIM group."""

    id: str
    name: str
    display_name: str | None = None

    @classmethod
    def from_raw(cls, raw: Mapping[str, object] | object) -> "Group":
        try:
            identifier = str(_get_value(raw, "id", required=True))
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise ValueError("SIM group payload missing required fields") from exc
        raw_name = _get_value(raw, "name", "groupName")
        if isinstance(raw_name, str):
            name = raw_name
        else:
            name = identifier
        display_name = _get_value(raw, "displayName", "display_name")
        if display_name is not None:
            display_name = str(display_name)
        return cls(id=identifier, name=name, display_name=display_name)


@dataclass(slots=True)
class Member:
    """Representation of a SIM group member."""

    person_id: str
    group_id: str
    primary_email: str | None = None
    emails: Sequence[str] = field(default_factory=tuple)
    display_name: str | None = None

    @classmethod
    def from_raw(cls, raw: Mapping[str, object] | object, group_id: str) -> "Member":
        try:
            person_id = str(_get_value(raw, "personId", "person_id", required=True))
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise ValueError("SIM member payload missing personId") from exc
        primary_email = _get_value(raw, "primaryEmail", "primary_email")
        emails: Sequence[str]
        raw_emails = _get_value(raw, "emails")
        if isinstance(raw_emails, Iterable):
            emails = tuple(str(email) for email in raw_emails)
        else:
            emails = tuple()
        if isinstance(primary_email, str):
            primary_email = primary_email
        else:
            primary_email = None
        display_name = _get_value(raw, "displayName", "display_name")
        if isinstance(display_name, str):
            display_name = display_name
        else:
            display_name = None
        return cls(
            person_id=person_id,
            group_id=group_id,
            primary_email=primary_email,
            emails=emails,
            display_name=display_name,
        )


@dataclass(slots=True)
class User:
    """Representation of a SIM user record."""

    person_id: str
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    emails: Sequence[str] = field(default_factory=tuple)

    @classmethod
    def from_raw(cls, raw: Mapping[str, object] | object) -> "User":
        try:
            person_id = str(_get_value(raw, "personId", "person_id", required=True))
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise ValueError("SIM user payload missing personId") from exc
        first_name = _get_value(raw, "firstName", "first_name")
        last_name = _get_value(raw, "lastName", "last_name")
        display_name = _get_value(raw, "displayName", "display_name")
        emails: Sequence[str]
        raw_emails = _get_value(raw, "emails")
        if isinstance(raw_emails, Iterable):
            emails = tuple(str(email) for email in raw_emails)
        else:
            emails = tuple()
        return cls(
            person_id=person_id,
            display_name=str(display_name) if isinstance(display_name, str) else None,
            first_name=str(first_name) if isinstance(first_name, str) else None,
            last_name=str(last_name) if isinstance(last_name, str) else None,
            emails=emails,
        )


RawMapping = Mapping[str, object] | MutableMapping[str, object]
