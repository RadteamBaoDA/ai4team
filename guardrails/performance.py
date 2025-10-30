"""
Performance monitoring and metrics collection for Ollama Guard Proxy
Optimized for macOS Apple Silicon servers
"""

import logging
import time
import platform
import psutil
import os
from typing import Dict, Any, Optional
from datetime import datetime
from collections import deque
import threading

logger = logging.getLogger(__name__)

# Try to import torch for GPU monitoring
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class PerformanceMonitor:
    """Monitor system and application performance metrics."""
    
    def __init__(self, history_size: int = 100):
        """
        Initialize performance monitor.
        
        Args:
            history_size: Number of historical measurements to keep
        """
        self.history_size = history_size
        self.start_time = time.time()
        
        # Metrics history
        self.cpu_history = deque(maxlen=history_size)
        self.memory_history = deque(maxlen=history_size)
        self.request_history = deque(maxlen=history_size)
        
        # Request counters
        self.total_requests = 0
        self.total_errors = 0
        self.lock = threading.RLock()
        
        # Detect platform
        self.platform_info = self._detect_platform()
        
        logger.info(f'Performance monitor initialized: {self.platform_info["description"]}')
    
    def _detect_platform(self) -> Dict[str, Any]:
        """Detect platform and hardware information."""
        system = platform.system()
        machine = platform.machine()
        
        info = {
            'system': system,
            'machine': machine,
            'python_version': platform.python_version(),
            'cpu_count': os.cpu_count() or 1,
        }
        
        # macOS specific information
        if system == 'Darwin':
            info['is_macos'] = True
            info['is_apple_silicon'] = machine == 'arm64'
            
            if machine == 'arm64':
                info['description'] = 'macOS Apple Silicon (M1/M2/M3)'
            else:
                info['description'] = f'macOS {machine}'
        else:
            info['is_macos'] = False
            info['is_apple_silicon'] = False
            info['description'] = f'{system} {machine}'
        
        # GPU information
        if HAS_TORCH:
            info['pytorch_version'] = torch.__version__
            info['mps_available'] = torch.backends.mps.is_available() if hasattr(torch.backends, 'mps') else False
            info['cuda_available'] = torch.cuda.is_available()
            
            if info['mps_available']:
                info['gpu_type'] = 'MPS (Apple Silicon)'
            elif info['cuda_available']:
                info['gpu_type'] = f'CUDA ({torch.cuda.get_device_name(0)})'
            else:
                info['gpu_type'] = 'None (CPU only)'
        else:
            info['pytorch_version'] = 'Not installed'
            info['gpu_type'] = 'Unknown (PyTorch not available)'
        
        return info
    
    def record_request(self, success: bool = True, duration: float = 0.0) -> None:
        """Record a request completion."""
        with self.lock:
            self.total_requests += 1
            if not success:
                self.total_errors += 1
            
            self.request_history.append({
                'timestamp': time.time(),
                'success': success,
                'duration': duration
            })
    
    def get_cpu_metrics(self) -> Dict[str, Any]:
        """Get CPU usage metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            metrics = {
                'usage_percent': round(cpu_percent, 2),
                'count': cpu_count,
            }
            
            if cpu_freq:
                metrics['frequency_mhz'] = round(cpu_freq.current, 2)
                metrics['min_frequency_mhz'] = round(cpu_freq.min, 2)
                metrics['max_frequency_mhz'] = round(cpu_freq.max, 2)
            
            # Per-core usage
            per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
            metrics['per_core'] = [round(p, 2) for p in per_cpu]
            
            # Add to history
            with self.lock:
                self.cpu_history.append({
                    'timestamp': time.time(),
                    'usage': cpu_percent
                })
            
            return metrics
        except Exception as e:
            logger.error(f'Failed to get CPU metrics: {e}')
            return {'error': str(e)}
    
    def get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory usage metrics."""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            metrics = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'usage_percent': round(memory.percent, 2),
                'swap_total_gb': round(swap.total / (1024**3), 2),
                'swap_used_gb': round(swap.used / (1024**3), 2),
                'swap_percent': round(swap.percent, 2),
            }
            
            # Process-specific memory
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info()
            
            metrics['process_rss_mb'] = round(process_memory.rss / (1024**2), 2)
            metrics['process_vms_mb'] = round(process_memory.vms / (1024**2), 2)
            
            # Add to history
            with self.lock:
                self.memory_history.append({
                    'timestamp': time.time(),
                    'usage_percent': memory.percent,
                    'process_rss_mb': metrics['process_rss_mb']
                })
            
            return metrics
        except Exception as e:
            logger.error(f'Failed to get memory metrics: {e}')
            return {'error': str(e)}
    
    def get_disk_metrics(self) -> Dict[str, Any]:
        """Get disk usage metrics."""
        try:
            disk = psutil.disk_usage('/')
            
            return {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'usage_percent': round(disk.percent, 2),
            }
        except Exception as e:
            logger.error(f'Failed to get disk metrics: {e}')
            return {'error': str(e)}
    
    def get_network_metrics(self) -> Dict[str, Any]:
        """Get network I/O metrics."""
        try:
            net_io = psutil.net_io_counters()
            
            return {
                'bytes_sent_mb': round(net_io.bytes_sent / (1024**2), 2),
                'bytes_recv_mb': round(net_io.bytes_recv / (1024**2), 2),
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errors_in': net_io.errin,
                'errors_out': net_io.errout,
            }
        except Exception as e:
            logger.error(f'Failed to get network metrics: {e}')
            return {'error': str(e)}
    
    def get_gpu_metrics(self) -> Dict[str, Any]:
        """Get GPU metrics (MPS or CUDA)."""
        if not HAS_TORCH:
            return {'available': False, 'reason': 'PyTorch not installed'}
        
        metrics = {'available': False}
        
        try:
            # Check MPS (Apple Silicon)
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                metrics = {
                    'available': True,
                    'type': 'MPS',
                    'device': 'Apple Silicon GPU',
                    'driver_version': 'Built-in',
                }
                
                # Try to get memory info (may not be available on all macOS versions)
                try:
                    # MPS doesn't provide direct memory access, so we estimate
                    metrics['estimated_available'] = True
                except Exception:
                    pass
            
            # Check CUDA (NVIDIA)
            elif torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                current_device = torch.cuda.current_device()
                
                metrics = {
                    'available': True,
                    'type': 'CUDA',
                    'device_count': device_count,
                    'current_device': current_device,
                    'device_name': torch.cuda.get_device_name(current_device),
                }
                
                # Get memory info
                memory_allocated = torch.cuda.memory_allocated(current_device)
                memory_reserved = torch.cuda.memory_reserved(current_device)
                
                metrics['memory_allocated_mb'] = round(memory_allocated / (1024**2), 2)
                metrics['memory_reserved_mb'] = round(memory_reserved / (1024**2), 2)
            
            else:
                metrics['reason'] = 'No GPU available (CPU only)'
        
        except Exception as e:
            logger.error(f'Failed to get GPU metrics: {e}')
            metrics['error'] = str(e)
        
        return metrics
    
    def get_request_metrics(self) -> Dict[str, Any]:
        """Get request processing metrics."""
        with self.lock:
            total = self.total_requests
            errors = self.total_errors
            
            # Calculate request rate
            uptime = time.time() - self.start_time
            requests_per_second = total / uptime if uptime > 0 else 0
            
            # Calculate average duration from recent requests
            recent_requests = list(self.request_history)
            if recent_requests:
                durations = [r['duration'] for r in recent_requests if r['duration'] > 0]
                avg_duration = sum(durations) / len(durations) if durations else 0
                min_duration = min(durations) if durations else 0
                max_duration = max(durations) if durations else 0
            else:
                avg_duration = min_duration = max_duration = 0
            
            return {
                'total_requests': total,
                'total_errors': errors,
                'error_rate_percent': round((errors / total * 100) if total > 0 else 0, 2),
                'requests_per_second': round(requests_per_second, 2),
                'average_duration_ms': round(avg_duration * 1000, 2),
                'min_duration_ms': round(min_duration * 1000, 2),
                'max_duration_ms': round(max_duration * 1000, 2),
                'uptime_seconds': round(uptime, 2),
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all performance metrics."""
        return {
            'timestamp': datetime.now().isoformat(),
            'platform': self.platform_info,
            'cpu': self.get_cpu_metrics(),
            'memory': self.get_memory_metrics(),
            'disk': self.get_disk_metrics(),
            'network': self.get_network_metrics(),
            'gpu': self.get_gpu_metrics(),
            'requests': self.get_request_metrics(),
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of key metrics."""
        cpu = self.get_cpu_metrics()
        memory = self.get_memory_metrics()
        gpu = self.get_gpu_metrics()
        requests = self.get_request_metrics()
        
        summary = {
            'status': 'healthy',
            'uptime_seconds': requests['uptime_seconds'],
            'platform': self.platform_info['description'],
            'cpu_usage_percent': cpu.get('usage_percent', 0),
            'memory_usage_percent': memory.get('usage_percent', 0),
            'memory_process_mb': memory.get('process_rss_mb', 0),
            'total_requests': requests['total_requests'],
            'requests_per_second': requests['requests_per_second'],
            'error_rate_percent': requests['error_rate_percent'],
        }
        
        # Add GPU info if available
        if gpu.get('available'):
            summary['gpu_type'] = gpu.get('type')
            summary['gpu_device'] = gpu.get('device') or gpu.get('device_name')
        
        # Health status
        if cpu.get('usage_percent', 0) > 90:
            summary['status'] = 'warning'
            summary['warning'] = 'High CPU usage'
        elif memory.get('usage_percent', 0) > 90:
            summary['status'] = 'warning'
            summary['warning'] = 'High memory usage'
        elif requests['error_rate_percent'] > 10:
            summary['status'] = 'warning'
            summary['warning'] = 'High error rate'
        
        return summary


# Global performance monitor instance
_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get or create the global performance monitor."""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


def record_request(success: bool = True, duration: float = 0.0) -> None:
    """Record a request (convenience function)."""
    get_monitor().record_request(success, duration)
