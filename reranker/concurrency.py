"""Concurrency primitives for the reranker service."""

from __future__ import annotations

import asyncio
from typing import Optional


class QueueFullError(Exception):
    """Raised when the waiting queue has reached capacity."""


class QueueTimeoutError(Exception):
    """Raised when a request waits too long for an execution slot."""


class ConcurrencyController:
    """Controls parallel execution and optional waiting queue length."""

    def __init__(self, max_parallel: int, max_queue: Optional[int], queue_timeout: Optional[float]):
        if max_parallel < 1:
            raise ValueError("max_parallel must be at least 1")
        self._parallel_sem = asyncio.Semaphore(max_parallel)
        self._lock = asyncio.Lock()
        self._waiting = 0
        self._max_waiting = max_queue
        self._timeout = None if queue_timeout is None or queue_timeout < 0 else queue_timeout

    async def acquire(self) -> None:
        """Acquire an execution slot, waiting up to the configured timeout."""
        async with self._lock:
            if self._max_waiting is not None and self._waiting >= self._max_waiting:
                raise QueueFullError("Queue is full")
            self._waiting += 1

        try:
            if self._timeout is not None:
                await asyncio.wait_for(self._parallel_sem.acquire(), timeout=self._timeout)
            else:
                await self._parallel_sem.acquire()
        except asyncio.TimeoutError as exc:
            async with self._lock:
                self._waiting -= 1
            raise QueueTimeoutError("Timed out waiting for execution slot") from exc

        async with self._lock:
            self._waiting -= 1

    def release(self) -> None:
        """Release an execution slot."""
        self._parallel_sem.release()

    @property
    def waiting(self) -> int:
        """Return the current length of the waiting queue."""
        return self._waiting
