"""
Performance Monitoring and Alerting Module

This module provides comprehensive performance monitoring capabilities including:
- Real-time performance metrics collection
- Threshold-based alerting system
- Performance degradation detection
- Resource utilization monitoring
- Transformation pipeline performance tracking
- Circuit breaker integration
- Performance trend analysis

The module integrates with our structured logging framework and error recovery
mechanisms to provide complete observability for the transformation pipeline.
"""

import time
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, NamedTuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import asyncio

# Make psutil optional for environments where it's not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None  # type: ignore

from core.structured_logging import get_structured_logger, TransformationPhase
from core.exceptions import ServiceError, APIError

# Configure logging
logger = get_structured_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of performance metrics."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    TRANSFORMATION_TIME = "transformation_time"
    QUEUE_DEPTH = "queue_depth"
    QUEUE_LATENCY = "queue_latency"
    VERIFICATION_DURATION = "verification_duration"
    SUCCESS_RATE = "success_rate"


class ThresholdType(Enum):
    """Types of threshold comparisons."""
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"
    PERCENTAGE_CHANGE = "percentage_change"


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    name: str
    value: float
    timestamp: float
    metric_type: MetricType
    tags: Dict[str, str] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    execution_id: Optional[str] = None


@dataclass
class AlertThreshold:
    """Configuration for performance alert thresholds."""
    metric_name: str
    threshold_value: float
    threshold_type: ThresholdType
    severity: AlertSeverity
    window_seconds: int = 300  # 5 minutes
    min_samples: int = 3
    enabled: bool = True
    description: str = ""


@dataclass
class PerformanceAlert:
    """Performance alert instance."""
    alert_id: str
    metric_name: str
    current_value: float
    threshold_value: float
    severity: AlertSeverity
    message: str
    timestamp: float
    correlation_id: Optional[str] = None
    execution_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[float] = None


class MetricWindow:
    """Sliding window for metric calculations."""
    
    def __init__(self, window_seconds: int, max_size: int = 1000):
        self.window_seconds = window_seconds
        self.max_size = max_size
        self.data: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()
    
    def add_value(self, value: float, timestamp: Optional[float] = None):
        """Add a value to the window."""
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            self.data.append((timestamp, value))
            self._cleanup_old_data(timestamp)
    
    def get_values_in_window(self, current_time: Optional[float] = None) -> List[float]:
        """Get all values within the current window."""
        if current_time is None:
            current_time = time.time()
        
        cutoff_time = current_time - self.window_seconds
        
        with self._lock:
            return [value for timestamp, value in self.data if timestamp >= cutoff_time]
    
    def get_statistics(self, current_time: Optional[float] = None) -> Dict[str, float]:
        """Get statistical summary of values in window."""
        values = self.get_values_in_window(current_time)
        
        if not values:
            return {
                "count": 0,
                "mean": 0.0,
                "median": 0.0,
                "min": 0.0,
                "max": 0.0,
                "std_dev": 0.0
            }
        
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0
        }
    
    def _cleanup_old_data(self, current_time: float):
        """Remove data points outside the window."""
        cutoff_time = current_time - self.window_seconds
        
        while self.data and self.data[0][0] < cutoff_time:
            self.data.popleft()


class PerformanceMonitor:
    """
    Main performance monitoring class that collects metrics,
    evaluates thresholds, and generates alerts.
    """
    
    def __init__(self):
        self.metrics: Dict[str, MetricWindow] = {}
        self.thresholds: Dict[str, AlertThreshold] = {}
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_history: List[PerformanceAlert] = []
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # Performance tracking
        self.operation_timers: Dict[str, float] = {}
        self.transformation_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # System resource monitoring (disabled if psutil not available)
        self.system_monitor_enabled = PSUTIL_AVAILABLE
        self.system_monitor_interval = 30  # seconds
        self._system_monitor_task: Optional[asyncio.Task] = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize default thresholds
        self._setup_default_thresholds()
        
        logger.info("Performance monitor initialized")
    
    def _setup_default_thresholds(self):
        """Set up default performance thresholds."""
        default_thresholds = [
            AlertThreshold(
                metric_name="transformation_latency",
                threshold_value=2000.0,  # 2 seconds
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.HIGH,
                description="Transformation taking longer than 2 seconds"
            ),
            AlertThreshold(
                metric_name="api_response_time",
                threshold_value=200.0,  # 200ms
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.MEDIUM,
                description="API response time exceeding 200ms"
            ),
            AlertThreshold(
                metric_name="error_rate",
                threshold_value=5.0,  # 5%
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.HIGH,
                description="Error rate exceeding 5%"
            ),
            AlertThreshold(
                metric_name="memory_usage",
                threshold_value=85.0,  # 85%
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.CRITICAL,
                description="Memory usage exceeding 85%"
            ),
            AlertThreshold(
                metric_name="cpu_usage",
                threshold_value=90.0,  # 90%
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.HIGH,
                description="CPU usage exceeding 90%"
            ),
            AlertThreshold(
                metric_name="queue_latency",
                threshold_value=5000.0,  # 5 seconds
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.HIGH,
                description="Queue latency exceeding 5 seconds"
            ),
            AlertThreshold(
                metric_name="verification_duration",
                threshold_value=30000.0,  # 30 seconds
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.HIGH,
                description="Verification duration exceeding 30 seconds"
            )
        ]
        
        for threshold in default_thresholds:
            self.add_threshold(threshold)
    
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        tags: Optional[Dict[str, str]] = None,
        correlation_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ):
        """Record a performance metric."""
        timestamp = time.time()
        
        # Create metric window if it doesn't exist
        if name not in self.metrics:
            self.metrics[name] = MetricWindow(window_seconds=300)  # 5 minutes default
        
        # Add value to window
        self.metrics[name].add_value(value, timestamp)
        
        # Create metric object for logging
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=timestamp,
            metric_type=metric_type,
            tags=tags or {},
            correlation_id=correlation_id,
            execution_id=execution_id
        )
        
        # Log metric
        logger.debug(
            "Performance metric recorded",
            metric_name=name,
            metric_value=value,
            metric_type=metric_type.value,
            correlation_id=correlation_id,
            execution_id=execution_id,
            tags=tags
        )
        
        # Check thresholds
        self._check_thresholds(name, value, timestamp, correlation_id, execution_id, tags)
    
    def start_operation_timer(self, operation_name: str, correlation_id: Optional[str] = None) -> str:
        """Start timing an operation."""
        timer_key = f"{operation_name}:{correlation_id or 'default'}:{time.time()}"
        self.operation_timers[timer_key] = time.time()
        
        logger.debug(
            "Operation timer started",
            operation=operation_name,
            timer_key=timer_key,
            correlation_id=correlation_id
        )
        
        return timer_key
    
    def end_operation_timer(
        self,
        timer_key: str,
        operation_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> float:
        """End timing an operation and record the duration."""
        if timer_key not in self.operation_timers:
            logger.warn(
                "Timer key not found",
                timer_key=timer_key,
                operation=operation_name,
                correlation_id=correlation_id
            )
            return 0.0
        
        start_time = self.operation_timers.pop(timer_key)
        duration_ms = (time.time() - start_time) * 1000
        
        # Extract operation name from timer key if not provided
        if not operation_name:
            operation_name = timer_key.split(':')[0]
        
        # Record the latency metric
        self.record_metric(
            name=f"{operation_name}_latency",
            value=duration_ms,
            metric_type=MetricType.LATENCY,
            tags=tags,
            correlation_id=correlation_id,
            execution_id=execution_id
        )
        
        logger.debug(
            "Operation timer completed",
            operation=operation_name,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            execution_id=execution_id
        )
        
        return duration_ms
    
    def record_transformation_metrics(
        self,
        phase: TransformationPhase,
        duration_ms: float,
        success: bool,
        correlation_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        input_size: Optional[int] = None,
        output_size: Optional[int] = None,
        error_type: Optional[str] = None
    ):
        """Record transformation-specific performance metrics."""
        phase_name = phase.value
        
        # Record duration
        self.record_metric(
            name=f"transformation_{phase_name}_duration",
            value=duration_ms,
            metric_type=MetricType.TRANSFORMATION_TIME,
            correlation_id=correlation_id,
            execution_id=execution_id,
            tags={"phase": phase_name, "success": str(success)}
        )
        
        # Record success/failure
        self.record_metric(
            name=f"transformation_{phase_name}_success_rate",
            value=1.0 if success else 0.0,
            metric_type=MetricType.SUCCESS_RATE,
            correlation_id=correlation_id,
            execution_id=execution_id,
            tags={"phase": phase_name}
        )
        
        # Record throughput if sizes available
        if input_size is not None:
            throughput = input_size / (duration_ms / 1000) if duration_ms > 0 else 0
            self.record_metric(
                name=f"transformation_{phase_name}_throughput",
                value=throughput,
                metric_type=MetricType.THROUGHPUT,
                correlation_id=correlation_id,
                execution_id=execution_id,
                tags={"phase": phase_name}
            )
        
        # Record error metrics
        if not success and error_type:
            self.record_metric(
                name=f"transformation_{phase_name}_error_rate",
                value=1.0,
                metric_type=MetricType.ERROR_RATE,
                correlation_id=correlation_id,
                execution_id=execution_id,
                tags={"phase": phase_name, "error_type": error_type}
            )
    
    def add_threshold(self, threshold: AlertThreshold):
        """Add or update an alert threshold."""
        with self._lock:
            self.thresholds[threshold.metric_name] = threshold
        
        logger.info(
            "Alert threshold configured",
            metric_name=threshold.metric_name,
            threshold_value=threshold.threshold_value,
            threshold_type=threshold.threshold_type.value,
            severity=threshold.severity.value,
            enabled=threshold.enabled
        )
    
    def remove_threshold(self, metric_name: str):
        """Remove an alert threshold."""
        with self._lock:
            if metric_name in self.thresholds:
                del self.thresholds[metric_name]
                logger.info("Alert threshold removed", metric_name=metric_name)
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add a callback function to be called when alerts are triggered."""
        self.alert_callbacks.append(callback)
        logger.info("Alert callback registered")
    
    def get_metric_statistics(self, metric_name: str) -> Optional[Dict[str, float]]:
        """Get statistical summary for a metric."""
        if metric_name not in self.metrics:
            return None
        
        return self.metrics[metric_name].get_statistics()
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all currently active alerts."""
        with self._lock:
            return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[PerformanceAlert]:
        """Get alert history for the specified number of hours."""
        cutoff_time = time.time() - (hours * 3600)
        return [
            alert for alert in self.alert_history
            if alert.timestamp >= cutoff_time
        ]
    
    def resolve_alert(self, alert_id: str):
        """Manually resolve an active alert."""
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = time.time()
                
                # Move to history
                self.alert_history.append(alert)
                del self.active_alerts[alert_id]
                
                logger.info(
                    "Alert manually resolved",
                    alert_id=alert_id,
                    metric_name=alert.metric_name,
                    severity=alert.severity.value
                )
    
    def start_system_monitoring(self):
        """Start system resource monitoring."""
        if not PSUTIL_AVAILABLE:
            logger.warn("System monitoring disabled - psutil not available")
            return
            
        if self.system_monitor_enabled and not self._system_monitor_task:
            loop = asyncio.get_event_loop()
            self._system_monitor_task = loop.create_task(self._system_monitor_loop())
            logger.info("System monitoring started")
    
    def stop_system_monitoring(self):
        """Stop system resource monitoring."""
        if self._system_monitor_task:
            self._system_monitor_task.cancel()
            self._system_monitor_task = None
            logger.info("System monitoring stopped")
    
    async def _system_monitor_loop(self):
        """System monitoring loop."""
        if not PSUTIL_AVAILABLE:
            logger.warn("System monitoring loop cannot start - psutil not available")
            return
            
        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)  # type: ignore
                self.record_metric(
                    name="cpu_usage",
                    value=cpu_percent,
                    metric_type=MetricType.RESOURCE_USAGE,
                    tags={"resource": "cpu"}
                )
                
                # Memory usage
                memory = psutil.virtual_memory()  # type: ignore
                self.record_metric(
                    name="memory_usage",
                    value=memory.percent,
                    metric_type=MetricType.RESOURCE_USAGE,
                    tags={"resource": "memory"}
                )
                
                # Disk usage
                disk = psutil.disk_usage('/')  # type: ignore
                disk_percent = (disk.used / disk.total) * 100
                self.record_metric(
                    name="disk_usage",
                    value=disk_percent,
                    metric_type=MetricType.RESOURCE_USAGE,
                    tags={"resource": "disk"}
                )
                
                await asyncio.sleep(self.system_monitor_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Error in system monitoring loop",
                    exception=e,
                    error_type=type(e).__name__
                )
                await asyncio.sleep(self.system_monitor_interval)
    
    def _check_thresholds(
        self,
        metric_name: str,
        current_value: float,
        timestamp: float,
        correlation_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Check if metric value exceeds any configured thresholds."""
        if metric_name not in self.thresholds:
            return
        
        threshold = self.thresholds[metric_name]
        if not threshold.enabled:
            return
        
        # Get metric statistics for window-based thresholds
        stats = self.metrics[metric_name].get_statistics(timestamp)
        
        # Check if we have enough samples
        if stats["count"] < threshold.min_samples:
            return
        
        # Evaluate threshold
        threshold_exceeded = False
        comparison_value = current_value
        
        if threshold.threshold_type == ThresholdType.GREATER_THAN:
            threshold_exceeded = comparison_value > threshold.threshold_value
        elif threshold.threshold_type == ThresholdType.LESS_THAN:
            threshold_exceeded = comparison_value < threshold.threshold_value
        elif threshold.threshold_type == ThresholdType.EQUALS:
            threshold_exceeded = abs(comparison_value - threshold.threshold_value) < 0.001
        elif threshold.threshold_type == ThresholdType.PERCENTAGE_CHANGE:
            # Use mean for percentage change calculations
            if stats["count"] > 1:
                baseline = stats["mean"]
                if baseline > 0:
                    percentage_change = ((comparison_value - baseline) / baseline) * 100
                    threshold_exceeded = abs(percentage_change) > threshold.threshold_value
        
        if threshold_exceeded:
            self._trigger_alert(
                threshold,
                current_value,
                timestamp,
                correlation_id,
                execution_id,
                tags
            )
        else:
            # Check if we should resolve any existing alerts
            self._check_alert_resolution(metric_name, current_value, timestamp)
    
    def _trigger_alert(
        self,
        threshold: AlertThreshold,
        current_value: float,
        timestamp: float,
        correlation_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Trigger a performance alert."""
        alert_id = f"{threshold.metric_name}_{int(timestamp)}"
        
        # Check if similar alert is already active
        existing_alert_key = f"{threshold.metric_name}_{threshold.severity.value}"
        if existing_alert_key in self.active_alerts:
            # Update existing alert with new value
            existing_alert = self.active_alerts[existing_alert_key]
            existing_alert.current_value = current_value
            existing_alert.timestamp = timestamp
            return
        
        # Create new alert
        alert = PerformanceAlert(
            alert_id=alert_id,
            metric_name=threshold.metric_name,
            current_value=current_value,
            threshold_value=threshold.threshold_value,
            severity=threshold.severity,
            message=f"{threshold.description or 'Threshold exceeded'}: {current_value} {threshold.threshold_type.value} {threshold.threshold_value}",
            timestamp=timestamp,
            correlation_id=correlation_id,
            execution_id=execution_id,
            tags=tags or {}
        )
        
        with self._lock:
            self.active_alerts[existing_alert_key] = alert
        
        # Log alert
        logger.warn(
            "Performance alert triggered",
            alert_id=alert_id,
            metric_name=threshold.metric_name,
            current_value=current_value,
            threshold_value=threshold.threshold_value,
            severity=threshold.severity.value,
            correlation_id=correlation_id,
            execution_id=execution_id
        )
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(
                    "Error in alert callback",
                    exception=e,
                    alert_id=alert_id
                )
    
    def _check_alert_resolution(
        self,
        metric_name: str,
        current_value: float,
        timestamp: float
    ):
        """Check if any active alerts for this metric should be resolved."""
        alerts_to_resolve = []
        
        with self._lock:
            for alert_key, alert in self.active_alerts.items():
                if alert.metric_name == metric_name and not alert.resolved:
                    threshold = self.thresholds.get(metric_name)
                    if threshold:
                        # Check if current value is back within threshold
                        within_threshold = False
                        
                        if threshold.threshold_type == ThresholdType.GREATER_THAN:
                            within_threshold = current_value <= threshold.threshold_value
                        elif threshold.threshold_type == ThresholdType.LESS_THAN:
                            within_threshold = current_value >= threshold.threshold_value
                        
                        if within_threshold:
                            alerts_to_resolve.append(alert_key)
        
        # Resolve alerts
        for alert_key in alerts_to_resolve:
            with self._lock:
                if alert_key in self.active_alerts:
                    alert = self.active_alerts[alert_key]
                    alert.resolved = True
                    alert.resolved_at = timestamp
                    
                    # Move to history
                    self.alert_history.append(alert)
                    del self.active_alerts[alert_key]
                    
                    logger.info(
                        "Performance alert auto-resolved",
                        alert_id=alert.alert_id,
                        metric_name=alert.metric_name,
                        current_value=current_value
                    )


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _performance_monitor


def performance_timer(operation_name: str):
    """
    Decorator for automatic performance timing.
    
    Usage:
        @performance_timer("database_query")
        def query_database():
            # Function implementation
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract correlation_id from kwargs if available
            correlation_id = kwargs.get('correlation_id')
            execution_id = kwargs.get('execution_id')
            
            # Start timer
            timer_key = _performance_monitor.start_operation_timer(
                operation_name,
                correlation_id
            )
            
            try:
                result = func(*args, **kwargs)
                
                # Record success
                _performance_monitor.record_metric(
                    name=f"{operation_name}_success_rate",
                    value=1.0,
                    metric_type=MetricType.SUCCESS_RATE,
                    correlation_id=correlation_id,
                    execution_id=execution_id
                )
                
                return result
                
            except Exception as e:
                # Record failure
                _performance_monitor.record_metric(
                    name=f"{operation_name}_success_rate",
                    value=0.0,
                    metric_type=MetricType.SUCCESS_RATE,
                    correlation_id=correlation_id,
                    execution_id=execution_id,
                    tags={"error_type": type(e).__name__}
                )
                
                raise
            finally:
                # End timer
                _performance_monitor.end_operation_timer(
                    timer_key,
                    operation_name,
                    correlation_id,
                    execution_id
                )
        
        return wrapper
    return decorator


# Convenience functions for common monitoring patterns
def record_api_latency(endpoint: str, duration_ms: float, correlation_id: Optional[str] = None):
    """Record API endpoint latency."""
    _performance_monitor.record_metric(
        name=f"api_{endpoint}_latency",
        value=duration_ms,
        metric_type=MetricType.LATENCY,
        correlation_id=correlation_id,
        tags={"endpoint": endpoint}
    )


def record_transformation_performance(
    phase: TransformationPhase,
    duration_ms: float,
    success: bool,
    correlation_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    **kwargs
):
    """Record transformation phase performance."""
    _performance_monitor.record_transformation_metrics(
        phase=phase,
        duration_ms=duration_ms,
        success=success,
        correlation_id=correlation_id,
        execution_id=execution_id,
        **kwargs
    )


def record_queue_latency(
    enqueue_time: float,
    consume_time: float,
    correlation_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    event_id: Optional[str] = None,
    task_id: Optional[str] = None
):
    """
    Record queue latency metric measuring time from event enqueue to worker consumption.
    
    Args:
        enqueue_time: Timestamp when event was enqueued (seconds since epoch)
        consume_time: Timestamp when worker started consuming (seconds since epoch)
        correlation_id: Optional correlation ID for distributed tracing
        execution_id: Optional execution identifier
        event_id: Optional event identifier
        task_id: Optional task identifier
    """
    latency_ms = (consume_time - enqueue_time) * 1000
    
    tags = {}
    if event_id:
        tags["event_id"] = event_id
    if task_id:
        tags["task_id"] = task_id
    
    _performance_monitor.record_metric(
        name="queue_latency",
        value=latency_ms,
        metric_type=MetricType.QUEUE_LATENCY,
        correlation_id=correlation_id,
        execution_id=execution_id,
        tags=tags
    )


def record_verification_duration(
    start_time: float,
    end_time: float,
    verification_type: str,
    success: bool,
    correlation_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    project_id: Optional[str] = None,
    operation_details: Optional[Dict[str, str]] = None
):
    """
    Record verification duration metric measuring time for build/test verification operations.
    
    This function captures metrics for verification operations like npm ci, npm run build,
    and other build/test verification steps, providing observability for verification
    performance and enabling monitoring and alerting.
    
    Args:
        start_time: Timestamp when verification started (seconds since epoch)
        end_time: Timestamp when verification completed (seconds since epoch)
        verification_type: Type of verification (e.g., "npm_ci", "npm_build", "git_merge")
        success: Whether the verification operation succeeded
        correlation_id: Optional correlation ID for distributed tracing
        execution_id: Optional execution identifier
        project_id: Optional project identifier
        operation_details: Optional additional operation details for tagging
    """
    duration_ms = (end_time - start_time) * 1000
    
    tags = {
        "verification_type": verification_type,
        "success": str(success)
    }
    
    if project_id:
        tags["project_id"] = project_id
    
    if operation_details:
        # Add operation details to tags, ensuring string values
        for key, value in operation_details.items():
            if isinstance(value, str) and key not in tags:
                tags[key] = value
    
    _performance_monitor.record_metric(
        name="verification_duration",
        value=duration_ms,
        metric_type=MetricType.VERIFICATION_DURATION,
        correlation_id=correlation_id,
        execution_id=execution_id,
        tags=tags
    )


def setup_default_alert_callback():
    """Set up default alert callback that logs to structured logger."""
    def default_alert_callback(alert: PerformanceAlert):
        logger.warn(
            "Performance alert callback triggered",
            alert_id=alert.alert_id,
            metric_name=alert.metric_name,
            current_value=alert.current_value,
            threshold_value=alert.threshold_value,
            severity=alert.severity.value,
            alert_message=alert.message,
            correlation_id=alert.correlation_id,
            execution_id=alert.execution_id
        )
    
    _performance_monitor.add_alert_callback(default_alert_callback)


# Initialize default alert callback
setup_default_alert_callback()