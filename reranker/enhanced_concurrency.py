"""Optimized concurrency controller with atomic operations and efficient waiting."""

from __future__ import annotations

import asyncio
from typing import Optional


class QueueFullError(Exception):
    """Raised when the waiting queue has reached capacity."""


class QueueTimeoutError(Exception):
    """Raised when a request waits too long for an execution slot."""


class OptimizedConcurrencyController:
    """Optimized concurrency controller with atomic operations and efficient waiting."""

    def __init__(
        self,
        max_parallel: int,
        max_queue: Optional[int],
        queue_timeout: Optional[float],
        request_timeout: Optional[float] = 300.0,
    ):
        if max_parallel < 1:
            raise ValueError("max_parallel must be at least 1")

        self._parallel_sem = asyncio.Semaphore(max_parallel)
        self._active_count = 0
        self._waiting_count = 0
        self._max_waiting = max_queue
        self._timeout = request_timeout

        # Atomic counters using asyncio lock
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire an execution slot with optimized waiting."""
        async with self._lock:
            if self._max_waiting is not None and self._waiting_count >= self._max_waiting:
                raise QueueFullError("Queue is full")
            self._waiting_count += 1

        try:
            if self._timeout is not None:
                await asyncio.wait_for(self._parallel_sem.acquire(), timeout=self._timeout)
            else:
                await self._parallel_sem.acquire()
        except asyncio.TimeoutError as exc:
            async with self._lock:
                self._waiting_count -= 1
            raise QueueTimeoutError("Timed out waiting for execution slot") from exc

        async with self._lock:
            self._waiting_count -= 1
            self._active_count += 1

    def release(self) -> None:
        """Release an execution slot."""
        self._parallel_sem.release()
        
        async def decrement():
            async with self._lock:
                self._active_count = max(0, self._active_count - 1)
        
        asyncio.create_task(decrement())

    @property
    def waiting(self) -> int:
        """Return the current number of waiting requests."""
        return self._waiting_count

    @property
    def active(self) -> int:
        """Return the current number of active requests."""
        return self._active_count

    @property
    def available_slots(self) -> int:
        """Return available execution slots."""
        return self._parallel_sem._value  # type: ignore


class RequestPool:
    """Pool for managing batched requests and document cache."""

    def __init__(self, max_pool_size: int = 8):
        self._max_pool_size = max_pool_size
        self._pool = []
        self._lock = asyncio.Lock()

    async def get_from_pool(self, key: str):
        """Get a cached request or return None if not found."""
        async with self._lock:
            # Simple LRU-like cache - in production, use Redis or similar
            # This is a simplified version for demonstration
            cached = None
            self._pool = [item for item in self._pool if not item.get('expired', False)]
            return cached

    async def add_to_pool(self, key: str, data):
        """Add request data to pool."""
        async with self._lock:
            if len(self._pool) >= self._max_pool_size:
                self._pool.pop(0)  # Remove oldest
            self._pool.append({'key': key, 'data': data})


class BatchProcessor:
    """Process requests in batches to improve throughput."""

    def __init__(self, batch_size: int = 4, max_wait_ms: float = 100.0):
        self._batch_size = batch_size
        self._max_wait_ns = max_wait_ms * 1_000_000
        self._pending_batches = []

    async def create_batch(self, requests_data: list):
        """Create a batch from requests."""
        if len(requests_data) >= self._batch_size:
            return await self._process_batch(requests_data[:self._batch_size])
        
        # For smaller batches, add a small delay to try to batch more requests
        try:
            await asyncio.sleep(self._max_wait_ns / 1_000_000_000)
            return await self._process_batch(requests_data)
        except Exception:
            # Process what we have if timeout or other error
            return await self._process_batch(requests_data)

    async def _process_batch(self, batch_data: list):
        """Process a batch of requests (override in service layer)."""
        # This is a placeholder - actual batch processing happens in the service
        results = []
        for data in batch_data:
            # Each item should be (query, documents, top_k, future)
            query, documents, top_k, future = data
            # Process would happen here
            results.append(future)
        return results


class ConcurrencyMetrics:
    """Track performance metrics for concurrency optimization."""

    def __init__(self):
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._avg_wait_time = 0.0
        self._avg_process_time = 0.0
        self._lock = asyncio.Lock()

    async def record_request(self, wait_time: float, process_time: float, success: bool):
        """Record metrics for a completed request."""
        async with self._lock:
            self._total_requests += 1
            if success:
                self._successful_requests += 1
            else:
                self._failed_requests += 1
            
            # Update running averages
            n = self._total_requests
            self._avg_wait_time = ((n - 1) * self._avg_wait_time + wait_time) / n
            self._avg_process_time = ((n - 1) * self._avg_process_time + process_time) / n

    def get_stats(self):
        """Get current metrics."""
        return {
            'total_requests': self._total_requests,
            'success_rate': (self._successful_requests / max(1, self._total_requests)) * 100,
            'avg_wait_ms': self._avg_wait_time * 1000,
            'avg_process_ms': self._avg_process_time * 1000,
        }
