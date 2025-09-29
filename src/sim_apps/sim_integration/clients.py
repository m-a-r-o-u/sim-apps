"""Adapters around :mod:`sim_api_wrapper` clients."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from importlib import import_module
from typing import Any, ClassVar, ContextManager, Iterable, Mapping, Protocol

from .models import Group, Member, User

LOGGER = logging.getLogger(__name__)


class SupportsSimClient(Protocol):
    """Protocol for the subset of the SIM client used by the app."""

    def list_groups(self, service: str) -> list[dict[str, Any]]: ...

    def list_group_members(self, group: str) -> list[dict[str, Any]]: ...

    def get_group_members(self, group: str) -> list[dict[str, Any]]: ...

    def get_user(self, person_id: str) -> dict[str, Any]: ...


@dataclass(slots=True)
class SIMClientAdapter:
    """Thin adapter that converts raw SIM client payloads into models."""

    client: SupportsSimClient
    _context: ContextManager[SupportsSimClient] | None = None
    _CLIENT_FACTORY_ATTRS: ClassVar[tuple[str, ...]] = (
        "Client",
        "client",
        "get_client",
        "create_client",
        "factory",
    )
    _REQUIRED_METHODS: ClassVar[tuple[str, ...]] = (
        "list_groups",
        "get_user",
    )
    _GROUP_MEMBER_METHODS: ClassVar[tuple[str, ...]] = (
        "list_group_members",
        "get_group_members",
    )

    @classmethod
    def from_default(cls, **kwargs: Any) -> "SIMClientAdapter":
        """Instantiate the default client from :mod:`sim_api_wrapper`."""

        module = import_module("sim_api_wrapper")
        sim_api_client = getattr(module, "SimApiClient", None)
        if sim_api_client is not None:
            context = sim_api_client(**kwargs)
            client = context.__enter__()
            cls._ensure_client(client)
            return cls(client=client, _context=context)
        client = cls._resolve_client(module, kwargs)
        return cls(client=client)

    def __enter__(self) -> "SIMClientAdapter":
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> bool:
        self.close(exc_type, exc, exc_tb)
        return False

    def close(self, exc_type=None, exc=None, exc_tb=None) -> None:
        if self._context is not None:
            try:
                self._context.__exit__(exc_type, exc, exc_tb)
            finally:
                self._context = None

    @classmethod
    def _resolve_client(cls, target: Any, kwargs: dict[str, Any]) -> SupportsSimClient:
        """Resolve a SIM client instance from ``target``.

        ``target`` may be the :mod:`sim_api_wrapper` module itself, a nested
        object, or an already-instantiated client.  The method walks through a
        list of common attribute names used by the wrapper to expose the client
        factory and gracefully handles nested modules such as
        ``sim_api_wrapper.client.Client``.
        """

        visited: set[int] = set()

        def iter_candidates(obj: Any) -> Iterable[Any]:
            for attr in cls._CLIENT_FACTORY_ATTRS:
                try:
                    candidate = getattr(obj, attr)
                except AttributeError:
                    continue
                except Exception:  # pragma: no cover - defensive guard
                    LOGGER.debug(
                        "Skipping sim_api_wrapper candidate %s due to error", attr
                    )
                    continue
                else:
                    yield candidate

        def resolve(obj: Any) -> SupportsSimClient | None:
            identifier = id(obj)
            if identifier in visited:
                return None
            visited.add(identifier)

            if callable(obj):
                client_instance = obj(**kwargs)
            else:
                if cls._supports_required_methods(obj):
                    if kwargs:
                        msg = "sim_api_wrapper.Client is not callable and cannot accept keyword arguments"
                        raise TypeError(msg)
                    client_instance = obj
                else:
                    for candidate in iter_candidates(obj):
                        resolved = resolve(candidate)
                        if resolved is not None:
                            return resolved
                    return None

            return cls._ensure_client(client_instance)

        client = resolve(target)
        if client is None:
            attr_list = ", ".join(cls._CLIENT_FACTORY_ATTRS)
            msg = (
                "Could not resolve a sim_api_wrapper client. Expected a callable factory or"
                f" an object exposing {', '.join(cls._REQUIRED_METHODS + cls._GROUP_MEMBER_METHODS)}"
                f" (checked attributes: {attr_list})."
            )
            raise TypeError(msg)
        return client

    @classmethod
    def _supports_required_methods(cls, obj: Any) -> bool:
        return all(hasattr(obj, attr) for attr in cls._REQUIRED_METHODS) and any(
            hasattr(obj, attr) for attr in cls._GROUP_MEMBER_METHODS
        )

    @classmethod
    def _ensure_client(cls, client: SupportsSimClient) -> SupportsSimClient:
        for attr in cls._REQUIRED_METHODS:
            if not hasattr(client, attr):
                msg = f"Resolved sim_api_wrapper client is missing required method: {attr}"
                raise TypeError(msg)
        if not any(hasattr(client, attr) for attr in cls._GROUP_MEMBER_METHODS):
            members = " or ".join(cls._GROUP_MEMBER_METHODS)
            msg = f"Resolved sim_api_wrapper client is missing required group membership method ({members})"
            raise TypeError(msg)
        return client

    def list_groups(self, service: str) -> list[Group]:
        LOGGER.debug("Listing groups for service %s", service)
        raw_groups = self.client.list_groups(service)
        groups: list[Group] = []
        for raw in raw_groups:
            if isinstance(raw, Mapping):
                mapping: Mapping[str, object] | None = raw
            elif isinstance(raw, str):
                mapping = self._coerce_group_string(raw)
                if mapping is None:
                    LOGGER.warning("Skipping empty group payload string")
                    continue
            else:
                LOGGER.warning(
                    "Skipping group payload with unexpected type: %s",
                    type(raw).__name__,
                )
                continue
            try:
                groups.append(Group.from_raw(mapping))
            except ValueError as exc:
                LOGGER.warning("Skipping malformed group payload: %s", exc)
        return groups

    @staticmethod
    def _coerce_group_string(raw: str) -> Mapping[str, object] | None:
        payload = raw.strip()
        if not payload:
            return None
        try:
            decoded = json.loads(payload)
        except ValueError:
            decoded = None
        if isinstance(decoded, Mapping):
            return decoded
        return {"id": payload, "name": payload}

    def list_group_members(self, group: Group | str) -> list[Member]:
        group_id = group.id if isinstance(group, Group) else str(group)
        LOGGER.debug("Listing members for group %s", group_id)
        if hasattr(self.client, "list_group_members"):
            raw_members = self.client.list_group_members(group_id)
        else:
            raw_members = self.client.get_group_members(group_id)
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
