"""Core filter protocol and helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, TypeVar

T = TypeVar("T")


class Filter(Protocol[T]):
    """A simple callable filter that transforms ``T`` values."""

    def __call__(self, data: T, /, **kwargs: object) -> T:
        ...


def compose(*filters: Filter[T]) -> Filter[T]:
    """Compose ``filters`` into a single filter applied left to right."""

    def _composed(data: T, /, **kwargs: object) -> T:
        current = data
        for func in filters:
            current = func(current, **kwargs)
        return current

    return _composed


def apply_filters(data: Iterable[T], *filters: Filter[Iterable[T]]) -> Iterable[T]:
    """Apply an ordered chain of filters to an iterable ``data`` source."""

    composed = compose(*filters)
    return composed(data)


__all__ = ["Filter", "compose", "apply_filters"]
