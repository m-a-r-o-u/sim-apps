"""Simple pipeline implementation for composing SIM operations."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, MutableMapping

PipelineContext = MutableMapping[str, Any]

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineStep:
    name: str
    func: Callable[[PipelineContext], PipelineContext]


def pipeline_step(name: str) -> Callable[[Callable[[PipelineContext], PipelineContext]], PipelineStep]:
    """Decorator for pipeline steps."""

    def _wrapper(func: Callable[[PipelineContext], PipelineContext]) -> PipelineStep:
        return PipelineStep(name=name, func=func)

    return _wrapper


class Pipeline:
    """Base pipeline class composed of ordered steps."""

    def __init__(self, *, name: str, debug_dir: Path | None = None, logger: logging.Logger | None = None) -> None:
        self.name = name
        self.steps: list[PipelineStep] = []
        self.debug_dir = debug_dir
        self.logger = logger or LOGGER

    def add_step(self, step: PipelineStep) -> None:
        self.steps.append(step)

    def run(self, dry_run: bool, **kwargs: Any) -> PipelineContext:
        context: PipelineContext = dict(kwargs)
        context["dry_run"] = dry_run
        self.logger.debug("Starting pipeline %s with context keys: %s", self.name, list(context))
        for index, step in enumerate(self.steps, start=1):
            self.logger.info("[%s] Running step %s", self.name, step.name)
            self.logger.debug("[%s] Input context before %s: %s", self.name, step.name, context)
            context = step.func(context)
            self.logger.debug("[%s] Output context after %s: %s", self.name, step.name, context)
            if self.debug_dir:
                self._dump_debug(index, step.name, context)
        self.logger.debug("Completed pipeline %s", self.name)
        return context

    def _dump_debug(self, index: int, step_name: str, context: PipelineContext) -> None:
        if not self.debug_dir:
            return
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        filename = self.debug_dir / f"{index:02d}_{step_name}.json"
        serializable = {
            key: value
            for key, value in context.items()
            if isinstance(value, (str, int, float, bool, list, dict))
        }
        filename.write_text(json.dumps(serializable, indent=2, sort_keys=True))
        self.logger.debug("Dumped debug context to %s", filename)


__all__ = ["Pipeline", "PipelineContext", "PipelineStep", "pipeline_step"]
