"""Adapters around :mod:`sim_api_wrapper` clients."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Protocol

from .models import Group, Member, User

LOGGER = logging.getLogger(__name__)


class SupportsSimClient(Protocol):
    """Protocol for the subset of the SIM client used by the app."""

    def list_groups(self, service: str) -> list[dict[str, Any]]: ...

    def list_group_members(self, group: str) -> list[dict[str, Any]]: ...

    def get_user(self, person_id: str) -> dict[str, Any]: ...


@dataclass(slots=True)
class SIMClientAdapter:
    """Thin adapter that converts raw SIM client payloads into models."""

    client: SupportsSimClient

    @classmethod
    def from_default(cls, **kwargs: Any) -> "SIMClientAdapter":
        """Instantiate the default client from :mod:`sim_api_wrapper`."""

        module = import_module("sim_api_wrapper")
        client_cls = getattr(module, "Client")
        client = client_cls(**kwargs)
        return cls(client=client)

    def list_groups(self, service: str) -> list[Group]:
        LOGGER.debug("Listing groups for service %s", service)
        raw_groups = self.client.list_groups(service)
        groups: list[Group] = []
        for raw in raw_groups:
            try:
                groups.append(Group.from_raw(raw))
            except ValueError as exc:
                LOGGER.warning("Skipping malformed group payload: %s", exc)
        return groups

    def list_group_members(self, group: Group | str) -> list[Member]:
        group_id = group.id if isinstance(group, Group) else str(group)
        LOGGER.debug("Listing members for group %s", group_id)
        raw_members = self.client.list_group_members(group_id)
        members: list[Member] = []
        for raw in raw_members:
            try:
                members.append(Member.from_raw(raw, group_id=group_id))
            except ValueError as exc:
                LOGGER.warning("Skipping malformed member payload: %s", exc)
        return members

    def get_user(self, person_id: str) -> User:
        LOGGER.debug("Fetching user %s", person_id)
        raw_user = self.client.get_user(person_id)
        return User.from_raw(raw_user)


__all__ = ["SIMClientAdapter", "SupportsSimClient"]
