"""Pluggable stage executors for the reference worker."""

from worker.executors.draft_desk import draft_desk_executor

__all__ = ["draft_desk_executor"]
