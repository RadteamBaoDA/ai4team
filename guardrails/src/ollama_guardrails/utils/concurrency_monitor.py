"""
Real-time concurrency and task monitoring for Uvicorn proxy.

This module provides utilities to monitor concurrent connections, active tasks,
and request queue depth in real-time through debug logs.

Features:
    - Track active tasks/connections per endpoint
    - Monitor request queue depth
    - Real-time logging of concurrency metrics
    - Memory usage tracking
    - CPU usage tracking
    - Connection timeout handling
"""

import os
import time
import logging
import threading
from typing import Dict, Optional
from collections import defaultdict

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    psutil = None

PSUTIL_AVAILABLE = psutil is not None

logger = logging.getLogger(__name__)


class ConcurrencyMonitor:
    """Monitor concurrent connections and tasks in real-time."""
    
    def __init__(self, enable_debug: bool = True, update_interval: float = 5.0):
        """
        Initialize concurrency monitor.
        
        Args:
            enable_debug: Enable debug logging (default: True)
            update_interval: How often to update metrics (in seconds, default: 5.0)
        """
        self.enable_debug = enable_debug
        if self.enable_debug and not logger.isEnabledFor(logging.DEBUG):
            logger.setLevel(logging.DEBUG)
        self.update_interval = update_interval
        self.active_tasks: Dict[str, int] = defaultdict(int)  # endpoint -> count
        self.completed_tasks: Dict[str, int] = defaultdict(int)  # endpoint -> count
        self.queue_depth = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.monitor_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        # Performance metrics
        self.peak_concurrent = 0
        self.total_requests = 0
        self.failed_requests = 0
        
    def start(self) -> None:
        """Start the monitoring thread."""
        if self.is_running:
            return
            
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.debug("Concurrency monitor started")
        
    def stop(self) -> None:
        """Stop the monitoring thread."""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.debug("Concurrency monitor stopped")
        
    def increment_task(self, endpoint: str, count: int = 1) -> None:
        """
        Increment active task count for an endpoint.
        
        Args:
            endpoint: API endpoint path
            count: Number of tasks to add (default: 1)
        """
        with self.lock:
            self.active_tasks[endpoint] += count
            self.total_requests += count
            
            # Update peak concurrent
            current_total = sum(self.active_tasks.values())
            if current_total > self.peak_concurrent:
                self.peak_concurrent = current_total
                
            if self.enable_debug and count > 0:
                logger.debug(f"Task increment: {endpoint} (+{count}), "
                           f"Total active: {current_total}, "
                           f"Peak: {self.peak_concurrent}")
        
    def decrement_task(self, endpoint: str, count: int = 1, success: bool = True) -> None:
        """
        Decrement active task count for an endpoint.
        
        Args:
            endpoint: API endpoint path
            count: Number of tasks to remove (default: 1)
            success: Whether the task completed successfully (default: True)
        """
        with self.lock:
            self.active_tasks[endpoint] = max(0, self.active_tasks[endpoint] - count)
            self.completed_tasks[endpoint] += count
            
            if not success:
                self.failed_requests += count
                
            current_total = sum(self.active_tasks.values())
            
            if self.enable_debug and count > 0:
                status = "✓" if success else "✗"
                logger.debug(f"Task complete: {endpoint} {status} (-{count}), "
                           f"Total active: {current_total}, "
                           f"Completed: {self.completed_tasks[endpoint]}")
        
    def set_queue_depth(self, depth: int) -> None:
        """
        Update current request queue depth.
        
        Args:
            depth: Number of queued requests
        """
        with self.lock:
            self.queue_depth = depth
            
    def get_metrics(self) -> Dict:
        """
        Get current concurrency metrics.
        
        Returns:
            Dictionary with concurrency metrics
        """
        with self.lock:
            current_active = sum(self.active_tasks.values())
            uptime = time.time() - self.start_time
            
            return {
                'current_active': current_active,
                'peak_concurrent': self.peak_concurrent,
                'queue_depth': self.queue_depth,
                'total_requests': self.total_requests,
                'completed_requests': sum(self.completed_tasks.values()),
                'failed_requests': self.failed_requests,
                'uptime_seconds': uptime,
                'active_by_endpoint': dict(self.active_tasks),
                'completed_by_endpoint': dict(self.completed_tasks),
            }
        
    def _monitor_loop(self) -> None:
        """Internal monitoring loop."""
        process = None
        if PSUTIL_AVAILABLE and psutil is not None:
            try:
                process = psutil.Process(os.getpid())
            except Exception as e:  # pragma: no cover - diagnostics only
                logger.warning(f"Could not access process metrics: {e}")
                process = None
            
        while self.is_running:
            try:
                metrics = self.get_metrics()
                current_active = metrics['current_active']
                
                # Log metrics
                if self.enable_debug:
                    uptime_str = self._format_uptime(metrics['uptime_seconds'])
                    queue_info = f" | Queue: {self.queue_depth}" if self.queue_depth > 0 else ""
                    
                    logger.debug(f"[CONCURRENCY] Active: {current_active}/{self.peak_concurrent} | "
                               f"Total: {self.total_requests} | "
                               f"Failed: {self.failed_requests} | "
                               f"Uptime: {uptime_str}{queue_info}")
                    
                    # Log by endpoint
                    if self.active_tasks:
                        endpoint_str = " | ".join(
                            f"{ep}: {cnt}" for ep, cnt in sorted(
                                [(ep, cnt) for ep, cnt in self.active_tasks.items() if cnt > 0],
                                key=lambda x: x[1],
                                reverse=True
                            )
                        )
                        logger.debug(f"[ENDPOINTS] {endpoint_str}")
                    
                    # Log process metrics if available
                    if process and PSUTIL_AVAILABLE:
                        try:
                            cpu_percent = process.cpu_percent(interval=0.1)
                            memory_info = process.memory_info()
                            memory_mb = memory_info.rss / 1024 / 1024
                            logger.debug(f"[SYSTEM] CPU: {cpu_percent:.1f}% | "
                                       f"Memory: {memory_mb:.1f}MB | "
                                       f"Threads: {process.num_threads()}")
                        except Exception:
                            pass
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.update_interval)
    
    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime duration."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"
    
    def log_summary(self) -> None:
        """Log summary of all metrics."""
        metrics = self.get_metrics()
        
        logger.info("=" * 70)
        logger.info("CONCURRENCY MONITORING SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Uptime:              {self._format_uptime(metrics['uptime_seconds'])}")
        logger.info(f"Current Active:      {metrics['current_active']}")
        logger.info(f"Peak Concurrent:     {metrics['peak_concurrent']}")
        logger.info(f"Total Requests:      {metrics['total_requests']}")
        logger.info(f"Completed:           {metrics['completed_requests']}")
        logger.info(f"Failed:              {metrics['failed_requests']}")
        logger.info(f"Queue Depth:         {metrics['queue_depth']}")
        logger.info("-" * 70)
        logger.info("BY ENDPOINT:")
        for endpoint, count in sorted(
            metrics['active_by_endpoint'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            completed = metrics['completed_by_endpoint'].get(endpoint, 0)
            logger.info(f"  {endpoint}: active={count}, completed={completed}")
        logger.info("=" * 70)


# Global monitor instance
_monitor_instance: Optional[ConcurrencyMonitor] = None


def get_monitor() -> ConcurrencyMonitor:
    """Get or create global monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        enable_debug = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')
        update_interval = float(os.environ.get('MONITOR_UPDATE_INTERVAL', '5.0'))
        _monitor_instance = ConcurrencyMonitor(enable_debug=enable_debug, update_interval=update_interval)
    return _monitor_instance


def init_monitor() -> ConcurrencyMonitor:
    """Initialize and start the global monitor."""
    monitor = get_monitor()
    monitor.start()
    return monitor


def track_task(endpoint: str):
    """Decorator to track task execution."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            monitor = get_monitor()
            monitor.increment_task(endpoint)
            try:
                result = await func(*args, **kwargs)
                monitor.decrement_task(endpoint, success=True)
                return result
            except Exception:
                monitor.decrement_task(endpoint, success=False)
                raise
        
        def sync_wrapper(*args, **kwargs):
            monitor = get_monitor()
            monitor.increment_task(endpoint)
            try:
                result = func(*args, **kwargs)
                monitor.decrement_task(endpoint, success=True)
                return result
            except Exception:
                monitor.decrement_task(endpoint, success=False)
                raise
        
        # Return appropriate wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
