"""Filters for working with SIM group collections."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping, MutableMapping, Sequence

from ..sim_integration import Group

GroupSequence = Sequence[Group]


SUFFIX_AI_C = "-ai-c"
SUFFIX_AI_H_MCML = "-ai-h-mcml"


def _base_project_name(group_name: str) -> str:
    for suffix in (SUFFIX_AI_C, SUFFIX_AI_H_MCML):
        if group_name.endswith(suffix):
            return group_name[: -len(suffix)]
    return group_name


def _has_suffix(group_name: str, suffix: str) -> bool:
    return group_name.endswith(suffix)


def _group_index(groups: Iterable[Group]) -> Mapping[str, set[str]]:
    mapping: MutableMapping[str, set[str]] = defaultdict(set)
    for group in groups:
        base_name = _base_project_name(group.name)
        mapping[base_name].add(group.name)
    return mapping


def only_project_groups() -> callable:
    """Return a filter that keeps only base project groups."""

    def _filter(groups: GroupSequence, /, **_: object) -> list[Group]:
        return [group for group in groups if _base_project_name(group.name) == group.name]

    return _filter


def only_ai_c_groups() -> callable:
    """Return a filter that keeps only ``-ai-c`` functional groups."""

    def _filter(groups: GroupSequence, /, **_: object) -> list[Group]:
        return [group for group in groups if _has_suffix(group.name, SUFFIX_AI_C)]

    return _filter


def only_ai_h_mcml_groups() -> callable:
    """Return a filter that keeps only ``-ai-h-mcml`` functional groups."""

    def _filter(groups: GroupSequence, /, **_: object) -> list[Group]:
        return [group for group in groups if _has_suffix(group.name, SUFFIX_AI_H_MCML)]

    return _filter


def with_ai_c_companion() -> callable:
    """Return project groups that have a ``-ai-c`` companion group."""

    def _filter(groups: GroupSequence, /, **kwargs: object) -> list[Group]:
        universe = kwargs.get("all_groups", groups)
        indexed = _group_index(universe)
        return [
            group
            for group in groups
            if _base_project_name(group.name) == group.name
            and f"{group.name}{SUFFIX_AI_C}" in indexed.get(group.name, set())
        ]

    return _filter


def with_ai_h_mcml_companion() -> callable:
    """Return project groups that have a ``-ai-h-mcml`` companion group."""

    def _filter(groups: GroupSequence, /, **kwargs: object) -> list[Group]:
        universe = kwargs.get("all_groups", groups)
        indexed = _group_index(universe)
        return [
            group
            for group in groups
            if _base_project_name(group.name) == group.name
            and f"{group.name}{SUFFIX_AI_H_MCML}" in indexed.get(group.name, set())
        ]

    return _filter


def with_ai_c_but_without_ai_h_mcml() -> callable:
    """Return project groups that have ``-ai-c`` but not ``-ai-h-mcml`` companions."""

    def _filter(groups: GroupSequence, /, **kwargs: object) -> list[Group]:
        universe = kwargs.get("all_groups", groups)
        indexed = _group_index(universe)
        result: list[Group] = []
        for group in groups:
            if _base_project_name(group.name) != group.name:
                continue
            group_set = indexed.get(group.name, set())
            has_ai_c = f"{group.name}{SUFFIX_AI_C}" in group_set
            has_ai_h_mcml = f"{group.name}{SUFFIX_AI_H_MCML}" in group_set
            if has_ai_c and not has_ai_h_mcml:
                result.append(group)
        return result

    return _filter


__all__ = [
    "GroupSequence",
    "only_project_groups",
    "only_ai_c_groups",
    "only_ai_h_mcml_groups",
    "with_ai_c_companion",
    "with_ai_h_mcml_companion",
    "with_ai_c_but_without_ai_h_mcml",
]
