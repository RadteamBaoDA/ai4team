"""Micro-batching for efficient GPU utilization during bursty traffic."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("reranker")


@dataclass
class BatchRequest:
    """Individual request in a batch."""
    query: str
    documents: List[str]
    top_k: Optional[int]
    future: asyncio.Future
    arrival_time: float


class MicroBatcher:
    """
    Collects concurrent requests within a time window and batches them for GPU efficiency.
    
    Benefits:
    - Reduces GPU kernel launch overhead
    - Better memory locality
    - Higher throughput for bursty traffic
    """

    def __init__(
        self,
        process_fn: Callable,
        window_ms: float = 10.0,
        max_batch_size: int = 32,
        enabled: bool = True,
    ):
        """
        Args:
            process_fn: Function to process a batch. Signature: (query, documents, top_k) -> results
            window_ms: Maximum wait time to collect requests (milliseconds)
            max_batch_size: Maximum requests per batch
            enabled: Enable micro-batching (disable for debugging)
        """
        self.process_fn = process_fn
        self.window_ms = window_ms
        self.window_seconds = window_ms / 1000.0
        self.max_batch_size = max_batch_size
        self.enabled = enabled

        # Batch collection
        self._pending: List[BatchRequest] = []
        self._lock = asyncio.Lock()
        self._batch_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._total_requests = 0
        self._total_batches = 0
        self._batch_sizes: List[int] = []

    async def submit(self, query: str, documents: List[str], top_k: Optional[int]) -> List[Dict[str, Any]]:
        """
        Submit a request for batching.
        
        Returns the reranking results.
        """
        if not self.enabled:
            # Micro-batching disabled, process immediately
            return await asyncio.to_thread(self.process_fn, query, documents, top_k)

        # Create request with future
        future = asyncio.get_event_loop().create_future()
        request = BatchRequest(
            query=query,
            documents=documents,
            top_k=top_k,
            future=future,
            arrival_time=time.perf_counter(),
        )

        async with self._lock:
            self._pending.append(request)
            self._total_requests += 1

            # Start batch processing task if not running
            if self._batch_task is None or self._batch_task.done():
                self._batch_task = asyncio.create_task(self._process_batch_loop())

        # Wait for result
        return await future

    async def _process_batch_loop(self):
        """Process batches continuously while requests are pending."""
        try:
            while True:
                # Wait for window duration or until batch is full
                await asyncio.sleep(self.window_seconds)

                async with self._lock:
                    if not self._pending:
                        # No more requests, exit loop
                        break

                    # Extract batch (up to max_batch_size)
                    batch = self._pending[:self.max_batch_size]
                    self._pending = self._pending[self.max_batch_size:]

                # Process batch outside lock
                if batch:
                    await self._process_batch(batch)

        except Exception as exc:
            logger.error("Batch processing loop error: %s", exc)

    async def _process_batch(self, batch: List[BatchRequest]):
        """Process a collected batch of requests."""
        batch_size = len(batch)
        self._total_batches += 1
        self._batch_sizes.append(batch_size)

        # Keep only last 1000 batch sizes for stats
        if len(self._batch_sizes) > 1000:
            self._batch_sizes = self._batch_sizes[-1000:]

        logger.debug("Processing micro-batch of %d requests", batch_size)

        # Check if all requests are identical (common case for deduplication)
        if self._are_requests_identical(batch):
            # Process once and share result
            req = batch[0]
            try:
                start = time.perf_counter()
                result = await asyncio.to_thread(self.process_fn, req.query, req.documents, req.top_k)
                elapsed = time.perf_counter() - start
                
                logger.debug("Micro-batch: processed %d identical requests in %.3fs", batch_size, elapsed)
                
                # Share result with all futures
                for request in batch:
                    if not request.future.done():
                        request.future.set_result(result)
                        
            except Exception as exc:
                logger.error("Batch processing error: %s", exc)
                for request in batch:
                    if not request.future.done():
                        request.future.set_exception(exc)
        else:
            # Process each request individually (but still benefit from reduced overhead)
            await self._process_batch_individually(batch)

    def _are_requests_identical(self, batch: List[BatchRequest]) -> bool:
        """Check if all requests in batch are identical."""
        if len(batch) <= 1:
            return True

        first = batch[0]
        for req in batch[1:]:
            if (req.query != first.query or 
                req.documents != first.documents or 
                req.top_k != first.top_k):
                return False

        return True

    async def _process_batch_individually(self, batch: List[BatchRequest]):
        """Process each request in batch individually (in parallel threads)."""
        tasks = []
        
        for request in batch:
            task = asyncio.create_task(self._process_single_request(request))
            tasks.append(task)
        
        # Wait for all to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_single_request(self, request: BatchRequest):
        """Process a single request and set its future."""
        try:
            result = await asyncio.to_thread(
                self.process_fn,
                request.query,
                request.documents,
                request.top_k
            )
            
            if not request.future.done():
                request.future.set_result(result)
                
        except Exception as exc:
            logger.error("Request processing error: %s", exc)
            if not request.future.done():
                request.future.set_exception(exc)

    def get_stats(self) -> Dict[str, Any]:
        """Get micro-batching statistics."""
        if not self._batch_sizes:
            avg_batch_size = 0.0
        else:
            avg_batch_size = sum(self._batch_sizes) / len(self._batch_sizes)

        return {
            "enabled": self.enabled,
            "total_requests": self._total_requests,
            "total_batches": self._total_batches,
            "avg_batch_size": round(avg_batch_size, 2),
            "window_ms": self.window_ms,
            "max_batch_size": self.max_batch_size,
            "pending_requests": len(self._pending),
        }


def create_micro_batcher(process_fn: Callable) -> MicroBatcher:
    """Create micro-batcher with configuration from environment."""
    enabled = os.environ.get("MICRO_BATCH_ENABLED", "false").lower() == "true"
    window_ms = float(os.environ.get("MICRO_BATCH_WINDOW_MS", "10.0"))
    max_size = int(os.environ.get("MICRO_BATCH_MAX_SIZE", "32"))

    batcher = MicroBatcher(
        process_fn=process_fn,
        window_ms=window_ms,
        max_batch_size=max_size,
        enabled=enabled,
    )

    if enabled:
        logger.info(
            "Micro-batching enabled: window=%.1fms, max_size=%d",
            window_ms,
            max_size
        )
    else:
        logger.info("Micro-batching disabled")

    return batcher
