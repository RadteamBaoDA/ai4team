"""
Concurrency and Queue Management for Ollama Guard Proxy

This module implements Ollama-style concurrent request handling with:
1. OLLAMA_NUM_PARALLEL - Maximum parallel requests per model
2. OLLAMA_MAX_QUEUE - Maximum queued requests before rejection

Features:
- Per-model request queuing and parallelism control
- Adaptive parallel limits based on available memory
- Request queue management with configurable max size
- Graceful degradation when queue is full
- Metrics and monitoring for queue depth and processing times
"""

import asyncio
import logging
import time
import os
import platform
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ModelQueueStats:
    """Statistics for a model's request queue."""
    model_name: str
    parallel_limit: int
    queue_limit: int
    active_requests: int = 0
    queued_requests: int = 0
    total_processed: int = 0
    total_rejected: int = 0
    total_wait_time: float = 0.0
    total_processing_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


class RequestQueue:
    """Queue manager for a single model with parallelism control."""
    
    def __init__(
        self,
        model_name: str,
        parallel_limit: int = 4,
        queue_limit: int = 512
    ):
        """
        Initialize request queue for a model.
        
        Args:
            model_name: Name of the model
            parallel_limit: Max number of parallel requests
            queue_limit: Max number of queued requests
        """
        self.model_name = model_name
        self.parallel_limit = parallel_limit
        self.queue_limit = queue_limit
        
        # Semaphore to limit parallel execution
        self.semaphore = asyncio.Semaphore(parallel_limit)
        
        # Queue for pending requests
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_limit)
        
        # Statistics
        self.stats = ModelQueueStats(
            model_name=model_name,
            parallel_limit=parallel_limit,
            queue_limit=queue_limit
        )
        
        # Lock for stats updates
        self.stats_lock = asyncio.Lock()
        
        logger.info(
            f"Request queue initialized for model '{model_name}': "
            f"parallel={parallel_limit}, queue={queue_limit}"
        )
    
    async def execute(
        self,
        request_id: str,
        coro: Callable,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Execute a request with queuing and parallelism control.
        
        Args:
            request_id: Unique identifier for the request
            coro: Coroutine to execute
            timeout: Optional timeout in seconds
        
        Returns:
            Result from the coroutine
        
        Raises:
            asyncio.QueueFull: If queue is full
            asyncio.TimeoutError: If request times out
        """
        enqueue_time = time.time()
        
        # Try to enqueue (non-blocking)
        try:
            await asyncio.wait_for(
                self.queue.put(request_id),
                timeout=0.1  # Quick check
            )
        except asyncio.TimeoutError:
            async with self.stats_lock:
                self.stats.total_rejected += 1
            raise asyncio.QueueFull(
                f"Request queue full for model '{self.model_name}' "
                f"(max: {self.queue_limit})"
            )
        
        async with self.stats_lock:
            self.stats.queued_requests = self.queue.qsize()
        
        try:
            # Wait for semaphore slot
            async with self.semaphore:
                # Remove from queue
                await self.queue.get()
                
                wait_time = time.time() - enqueue_time
                process_start = time.time()
                
                async with self.stats_lock:
                    self.stats.active_requests += 1
                    self.stats.queued_requests = self.queue.qsize()
                    self.stats.total_wait_time += wait_time
                
                logger.debug(
                    f"Processing request {request_id} for model '{self.model_name}' "
                    f"(waited {wait_time:.3f}s)"
                )
                
                try:
                    # Execute the actual request
                    if timeout:
                        result = await asyncio.wait_for(coro, timeout=timeout)
                    else:
                        result = await coro
                    
                    process_time = time.time() - process_start
                    
                    async with self.stats_lock:
                        self.stats.total_processed += 1
                        self.stats.total_processing_time += process_time
                    
                    logger.debug(
                        f"Completed request {request_id} for model '{self.model_name}' "
                        f"(processed in {process_time:.3f}s)"
                    )
                    
                    return result
                
                finally:
                    async with self.stats_lock:
                        self.stats.active_requests -= 1
                        self.stats.queued_requests = self.queue.qsize()
        
        except asyncio.QueueFull:
            # Re-raise queue full errors
            raise
        except Exception as e:
            logger.error(
                f"Error processing request {request_id} for model '{self.model_name}': {e}"
            )
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get current statistics for this queue."""
        async with self.stats_lock:
            avg_wait = (
                self.stats.total_wait_time / self.stats.total_processed
                if self.stats.total_processed > 0
                else 0.0
            )
            avg_process = (
                self.stats.total_processing_time / self.stats.total_processed
                if self.stats.total_processed > 0
                else 0.0
            )
            
            return {
                "model": self.stats.model_name,
                "parallel_limit": self.stats.parallel_limit,
                "queue_limit": self.stats.queue_limit,
                "active_requests": self.stats.active_requests,
                "queued_requests": self.stats.queued_requests,
                "available_slots": self.parallel_limit - self.stats.active_requests,
                "queue_available": self.queue_limit - self.stats.queued_requests,
                "total_processed": self.stats.total_processed,
                "total_rejected": self.stats.total_rejected,
                "avg_wait_time_ms": round(avg_wait * 1000, 2),
                "avg_processing_time_ms": round(avg_process * 1000, 2),
                "uptime_seconds": (datetime.now() - self.stats.created_at).total_seconds()
            }


class ConcurrencyManager:
    """
    Global concurrency manager for all models.
    
    Implements Ollama-style concurrent request handling with per-model
    queues and parallelism control.
    """
    
    def __init__(
        self,
        default_parallel: Optional[int] = None,
        default_queue_limit: int = 512,
        auto_detect_parallel: bool = True
    ):
        """
        Initialize concurrency manager.
        
        Args:
            default_parallel: Default parallel limit (None = auto-detect)
            default_queue_limit: Default max queue size
            auto_detect_parallel: Auto-detect parallel limit based on memory
        """
        self.default_queue_limit = default_queue_limit
        
        # Auto-detect parallel limit if not specified
        if default_parallel is None and auto_detect_parallel:
            self.default_parallel = self._detect_parallel_limit()
        else:
            self.default_parallel = default_parallel or 4
        
        # Per-model queues
        self.model_queues: Dict[str, RequestQueue] = {}
        self.lock = asyncio.Lock()
        
        logger.info(
            f"Concurrency manager initialized: "
            f"default_parallel={self.default_parallel}, "
            f"default_queue_limit={self.default_queue_limit}"
        )
    
    def _detect_parallel_limit(self) -> int:
        """
        Auto-detect parallel limit based on available memory.
        
        Logic aligned with Ollama defaults:
        - Select either 4 or 1 based on available memory
        - Threshold: >= 16GB -> 4, otherwise -> 1
        """
        try:
            # Try to get available memory using platform-specific methods
            if platform.system() == "Linux":
                # Read from /proc/meminfo on Linux
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        if line.startswith('MemAvailable:'):
                            available_kb = int(line.split()[1])
                            available_gb = available_kb / (1024 ** 2)
                            parallel = 4 if available_gb >= 16 else 1
                            logger.info(
                                f"Auto-detected parallel limit: {parallel} "
                                f"(available memory: {available_gb:.2f}GB)"
                            )
                            return parallel
            elif platform.system() == "Darwin":  # macOS
                # Use sysctl on macOS
                import subprocess
                result = subprocess.run(['sysctl', 'hw.memsize'], capture_output=True, text=True)
                if result.returncode == 0:
                    total_bytes = int(result.stdout.split(':')[1].strip())
                    total_gb = total_bytes / (1024 ** 3)
                    # Assume 50% is available (rough estimate)
                    available_gb = total_gb * 0.5
                    parallel = 4 if available_gb >= 16 else 1
                    logger.info(
                        f"Auto-detected parallel limit: {parallel} "
                        f"(estimated available memory: {available_gb:.2f}GB)"
                    )
                    return parallel
            elif platform.system() == "Windows":
                # Use wmic on Windows
                import subprocess
                result = subprocess.run(
                    ['wmic', 'OS', 'get', 'FreePhysicalMemory'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        available_kb = int(lines[1].strip())
                        available_gb = available_kb / (1024 ** 2)
                        parallel = 4 if available_gb >= 16 else 1
                        logger.info(
                            f"Auto-detected parallel limit: {parallel} "
                            f"(available memory: {available_gb:.2f}GB)"
                        )
                        return parallel
            
            # Fallback if platform-specific detection fails
            logger.info("Could not detect memory, using default parallel limit: 4")
            return 4
        
        except Exception as e:
            logger.warning(f"Failed to auto-detect parallel limit: {e}. Using default 4.")
            return 4
    
    async def get_or_create_queue(
        self,
        model_name: str,
        parallel_limit: Optional[int] = None,
        queue_limit: Optional[int] = None
    ) -> RequestQueue:
        """
        Get or create a request queue for a model.
        
        Args:
            model_name: Name of the model
            parallel_limit: Override default parallel limit
            queue_limit: Override default queue limit
        
        Returns:
            RequestQueue for the model
        """
        async with self.lock:
            if model_name not in self.model_queues:
                self.model_queues[model_name] = RequestQueue(
                    model_name=model_name,
                    parallel_limit=parallel_limit or self.default_parallel,
                    queue_limit=queue_limit or self.default_queue_limit
                )
            
            return self.model_queues[model_name]
    
    async def execute(
        self,
        model_name: str,
        request_id: str,
        coro: Callable,
        timeout: Optional[float] = None,
        parallel_limit: Optional[int] = None,
        queue_limit: Optional[int] = None
    ) -> Any:
        """
        Execute a request with concurrency control.
        
        Args:
            model_name: Name of the model
            request_id: Unique identifier for the request
            coro: Coroutine to execute
            timeout: Optional timeout in seconds
            parallel_limit: Override default parallel limit for this model
            queue_limit: Override default queue limit for this model
        
        Returns:
            Result from the coroutine
        
        Raises:
            asyncio.QueueFull: If queue is full
            asyncio.TimeoutError: If request times out
        """
        queue = await self.get_or_create_queue(
            model_name,
            parallel_limit=parallel_limit,
            queue_limit=queue_limit
        )
        
        return await queue.execute(request_id, coro, timeout=timeout)
    
    async def get_stats(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for all models or a specific model.
        
        Args:
            model_name: Optional model name to get stats for
        
        Returns:
            Dictionary with statistics
        """
        async with self.lock:
            if model_name:
                if model_name in self.model_queues:
                    return await self.model_queues[model_name].get_stats()
                else:
                    return {
                        "error": f"No queue found for model '{model_name}'",
                        "available_models": list(self.model_queues.keys())
                    }
            else:
                # Get stats for all models
                stats = {
                    "default_parallel": self.default_parallel,
                    "default_queue_limit": self.default_queue_limit,
                    "total_models": len(self.model_queues),
                    "models": {}
                }
                
                for model, queue in self.model_queues.items():
                    stats["models"][model] = await queue.get_stats()
                
                return stats
    
    async def reset_stats(self, model_name: Optional[str] = None) -> None:
        """Reset statistics for all models or a specific model."""
        async with self.lock:
            if model_name:
                if model_name in self.model_queues:
                    # Recreate the queue to reset stats
                    old_queue = self.model_queues[model_name]
                    self.model_queues[model_name] = RequestQueue(
                        model_name=model_name,
                        parallel_limit=old_queue.parallel_limit,
                        queue_limit=old_queue.queue_limit
                    )
                    logger.info(f"Reset statistics for model '{model_name}'")
            else:
                # Reset all queues
                for model_name, old_queue in list(self.model_queues.items()):
                    self.model_queues[model_name] = RequestQueue(
                        model_name=model_name,
                        parallel_limit=old_queue.parallel_limit,
                        queue_limit=old_queue.queue_limit
                    )
                logger.info("Reset statistics for all models")
    
    async def update_limits(
        self,
        model_name: str,
        parallel_limit: Optional[int] = None,
        queue_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update limits for a specific model.
        
        Args:
            model_name: Name of the model
            parallel_limit: New parallel limit (None = keep current)
            queue_limit: New queue limit (None = keep current)
        
        Returns:
            Updated configuration
        """
        async with self.lock:
            if model_name in self.model_queues:
                old_queue = self.model_queues[model_name]
                
                new_parallel = parallel_limit if parallel_limit is not None else old_queue.parallel_limit
                new_queue = queue_limit if queue_limit is not None else old_queue.queue_limit
                
                # Create new queue with updated limits
                self.model_queues[model_name] = RequestQueue(
                    model_name=model_name,
                    parallel_limit=new_parallel,
                    queue_limit=new_queue
                )
                
                logger.info(
                    f"Updated limits for model '{model_name}': "
                    f"parallel={new_parallel}, queue={new_queue}"
                )
                
                return {
                    "model": model_name,
                    "parallel_limit": new_parallel,
                    "queue_limit": new_queue,
                    "status": "updated"
                }
            else:
                return {
                    "error": f"Model '{model_name}' not found",
                    "status": "not_found"
                }
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get current memory information."""
        try:
            memory_info = {}
            
            if platform.system() == "Linux":
                # Read from /proc/meminfo on Linux
                with open('/proc/meminfo', 'r') as f:
                    meminfo = {}
                    for line in f:
                        parts = line.split(':')
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip().split()[0]
                            meminfo[key] = int(value)
                    
                    total_gb = meminfo.get('MemTotal', 0) / (1024 ** 2)
                    available_gb = meminfo.get('MemAvailable', 0) / (1024 ** 2)
                    free_gb = meminfo.get('MemFree', 0) / (1024 ** 2)
                    used_gb = total_gb - available_gb
                    
                    memory_info = {
                        "total_gb": round(total_gb, 2),
                        "available_gb": round(available_gb, 2),
                        "used_gb": round(used_gb, 2),
                        "percent": round((used_gb / total_gb * 100) if total_gb > 0 else 0, 2),
                        "recommended_parallel": self._detect_parallel_limit()
                    }
            
            elif platform.system() == "Darwin":  # macOS
                import subprocess
                result = subprocess.run(['sysctl', 'hw.memsize'], capture_output=True, text=True)
                if result.returncode == 0:
                    total_bytes = int(result.stdout.split(':')[1].strip())
                    total_gb = total_bytes / (1024 ** 3)
                    # Rough estimate: assume 50% used
                    used_gb = total_gb * 0.5
                    available_gb = total_gb - used_gb
                    
                    memory_info = {
                        "total_gb": round(total_gb, 2),
                        "available_gb": round(available_gb, 2),
                        "used_gb": round(used_gb, 2),
                        "percent": 50.0,
                        "recommended_parallel": self._detect_parallel_limit()
                    }
            
            elif platform.system() == "Windows":
                import subprocess
                # Get total memory
                result_total = subprocess.run(
                    ['wmic', 'ComputerSystem', 'get', 'TotalPhysicalMemory'],
                    capture_output=True,
                    text=True
                )
                # Get available memory
                result_free = subprocess.run(
                    ['wmic', 'OS', 'get', 'FreePhysicalMemory'],
                    capture_output=True,
                    text=True
                )
                
                if result_total.returncode == 0 and result_free.returncode == 0:
                    total_lines = result_total.stdout.strip().split('\n')
                    free_lines = result_free.stdout.strip().split('\n')
                    
                    if len(total_lines) > 1 and len(free_lines) > 1:
                        total_bytes = int(total_lines[1].strip())
                        free_kb = int(free_lines[1].strip())
                        
                        total_gb = total_bytes / (1024 ** 3)
                        available_gb = free_kb / (1024 ** 2)
                        used_gb = total_gb - available_gb
                        
                        memory_info = {
                            "total_gb": round(total_gb, 2),
                            "available_gb": round(available_gb, 2),
                            "used_gb": round(used_gb, 2),
                            "percent": round((used_gb / total_gb * 100) if total_gb > 0 else 0, 2),
                            "recommended_parallel": self._detect_parallel_limit()
                        }
            
            if not memory_info:
                # Fallback if no platform-specific method worked
                memory_info = {
                    "error": "Memory info not available for this platform",
                    "recommended_parallel": 4
                }
            
            return memory_info
        
        except Exception as e:
            logger.error(f"Failed to get memory info: {e}")
            return {"error": str(e), "recommended_parallel": 4}
