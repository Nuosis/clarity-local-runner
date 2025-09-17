#!/usr/bin/env python3
"""
Centralized Metrics Collector for WebSocket Demo Client

This module provides comprehensive metrics collection, aggregation, and export
functionality for WebSocket reconnect behavior analysis. It integrates with
the existing structured logging patterns and provides multiple export formats.

Features:
- Real-time metrics collection and aggregation
- Historical metrics storage and analysis
- Multiple export formats (JSON, CSV)
- Performance trend analysis
- Metrics visualization helpers
- Integration with structured logging
"""

import asyncio
import csv
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from collections import deque
import statistics
import os

# Import structured logging from the project
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.structured_logging import get_structured_logger, LogStatus


@dataclass
class MetricsSnapshot:
    """A snapshot of metrics at a specific point in time."""
    timestamp: float
    reconnect_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    connection_state: str
    correlation_id: str


@dataclass
class MetricsAggregation:
    """Aggregated metrics over a time period."""
    start_time: float
    end_time: float
    total_reconnect_attempts: int
    successful_reconnects: int
    failed_reconnects: int
    success_rate_percent: float
    average_reconnect_time_s: float
    error_distribution: Dict[str, float]
    performance_summary: Dict[str, Any]
    state_distribution: Dict[str, float]


class MetricsCollector:
    """
    Centralized metrics collector for WebSocket reconnect behavior analysis.
    
    This class provides comprehensive metrics collection, aggregation, and export
    functionality with integration to structured logging patterns.
    """
    
    def __init__(self, max_snapshots: int = 1000, collection_interval: float = 5.0):
        """
        Initialize metrics collector.
        
        Args:
            max_snapshots: Maximum number of snapshots to keep in memory
            collection_interval: Interval between automatic metric collections (seconds)
        """
        self.max_snapshots = max_snapshots
        self.collection_interval = collection_interval
        
        # Metrics storage
        self.snapshots: deque = deque(maxlen=max_snapshots)
        self.aggregations: List[MetricsAggregation] = []
        
        # Collection state
        self.collecting = False
        self.collection_task: Optional[asyncio.Task] = None
        self.last_collection_time: Optional[float] = None
        
        # Correlation ID for this collector instance
        self.collector_id = str(uuid.uuid4())
        
        # Setup structured logging
        self.structured_logger = get_structured_logger(f"{__name__}.MetricsCollector")
        self.structured_logger.set_context(
            collector_id=self.collector_id,
            node="metrics_collector"
        )
    
    def collect_snapshot(self, websocket_client) -> MetricsSnapshot:
        """
        Collect a metrics snapshot from a WebSocket client.
        
        Args:
            websocket_client: WebSocketDemoClient instance to collect metrics from
            
        Returns:
            MetricsSnapshot containing current metrics
        """
        current_time = time.time()
        
        try:
            # Collect reconnect metrics
            reconnect_metrics = websocket_client.get_reconnect_metrics()
            
            # Collect performance metrics
            performance_metrics = websocket_client.get_performance_statistics()
            
            # Create snapshot
            snapshot = MetricsSnapshot(
                timestamp=current_time,
                reconnect_metrics=reconnect_metrics,
                performance_metrics=performance_metrics,
                connection_state=websocket_client.state.value,
                correlation_id=websocket_client.correlation_id
            )
            
            # Store snapshot
            self.snapshots.append(snapshot)
            self.last_collection_time = current_time
            
            # Log collection
            self.structured_logger.debug(
                "Metrics snapshot collected",
                status=LogStatus.COMPLETED,
                snapshot_timestamp=current_time,
                reconnect_attempts=reconnect_metrics["reconnect_attempts"],
                success_rate=reconnect_metrics["success_rate_percent"],
                connection_state=websocket_client.state.value
            )
            
            return snapshot
            
        except Exception as e:
            self.structured_logger.error(
                "Failed to collect metrics snapshot",
                status=LogStatus.FAILED,
                error=e
            )
            raise
    
    def start_collection(self, websocket_client) -> None:
        """
        Start automatic metrics collection.
        
        Args:
            websocket_client: WebSocketDemoClient instance to monitor
        """
        if self.collecting:
            return
        
        self.collecting = True
        self.collection_task = asyncio.create_task(
            self._collection_loop(websocket_client)
        )
        
        self.structured_logger.info(
            "Started automatic metrics collection",
            status=LogStatus.STARTED,
            collection_interval_s=self.collection_interval,
            max_snapshots=self.max_snapshots
        )
    
    async def stop_collection(self) -> None:
        """Stop automatic metrics collection."""
        self.collecting = False
        
        if self.collection_task and not self.collection_task.done():
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        self.structured_logger.info(
            "Stopped automatic metrics collection",
            status=LogStatus.COMPLETED,
            total_snapshots=len(self.snapshots)
        )
    
    async def _collection_loop(self, websocket_client) -> None:
        """Internal collection loop for automatic metrics gathering."""
        while self.collecting:
            try:
                self.collect_snapshot(websocket_client)
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.structured_logger.error(
                    "Error in metrics collection loop",
                    status=LogStatus.FAILED,
                    error=e
                )
                await asyncio.sleep(self.collection_interval)
    
    def aggregate_metrics(self, start_time: Optional[float] = None, 
                         end_time: Optional[float] = None) -> MetricsAggregation:
        """
        Aggregate metrics over a time period.
        
        Args:
            start_time: Start time for aggregation (defaults to first snapshot)
            end_time: End time for aggregation (defaults to last snapshot)
            
        Returns:
            MetricsAggregation containing aggregated metrics
        """
        if not self.snapshots:
            raise ValueError("No snapshots available for aggregation")
        
        # Determine time range - ensure we have float values
        actual_start_time: float = start_time if start_time is not None else self.snapshots[0].timestamp
        actual_end_time: float = end_time if end_time is not None else self.snapshots[-1].timestamp
        
        # Filter snapshots by time range
        filtered_snapshots = [
            s for s in self.snapshots
            if actual_start_time <= s.timestamp <= actual_end_time
        ]
        
        if not filtered_snapshots:
            raise ValueError("No snapshots found in specified time range")
        
        # Aggregate reconnect metrics
        total_attempts = 0
        successful_reconnects = 0
        failed_reconnects = 0
        reconnect_times = []
        error_categories = {}
        state_counts = {}
        
        # Performance metrics aggregation
        handshake_times = []
        latency_times = []
        
        for snapshot in filtered_snapshots:
            rm = snapshot.reconnect_metrics
            pm = snapshot.performance_metrics
            
            # Reconnect metrics
            total_attempts = max(total_attempts, rm["reconnect_attempts"])
            successful_reconnects = max(successful_reconnects, rm["successful_reconnects"])
            failed_reconnects = max(failed_reconnects, rm["failed_reconnects"])
            reconnect_times.extend(rm["reconnect_times_s"])
            
            # Error distribution
            for error_type, count in rm["error_categories"].items():
                error_categories[error_type] = max(error_categories.get(error_type, 0), count)
            
            # State distribution
            state = snapshot.connection_state
            state_counts[state] = state_counts.get(state, 0) + 1
            
            # Performance metrics
            if pm["handshake"]["statistics"]["avg"] > 0:
                handshake_times.append(pm["handshake"]["statistics"]["avg"])
            if pm["message_latency"]["statistics"]["avg"] > 0:
                latency_times.append(pm["message_latency"]["statistics"]["avg"])
        
        # Calculate aggregated values
        success_rate = (successful_reconnects / total_attempts * 100.0) if total_attempts > 0 else 0.0
        avg_reconnect_time = statistics.mean(reconnect_times) if reconnect_times else 0.0
        
        # Error distribution as percentages
        total_errors = sum(error_categories.values())
        error_distribution = {
            error_type: (count / total_errors * 100.0) if total_errors > 0 else 0.0
            for error_type, count in error_categories.items()
        }
        
        # State distribution as percentages
        total_states = sum(state_counts.values())
        state_distribution = {
            state: (count / total_states * 100.0) if total_states > 0 else 0.0
            for state, count in state_counts.items()
        }
        
        # Performance summary
        performance_summary = {
            "handshake": {
                "avg_ms": statistics.mean(handshake_times) if handshake_times else 0.0,
                "min_ms": min(handshake_times) if handshake_times else 0.0,
                "max_ms": max(handshake_times) if handshake_times else 0.0,
                "samples": len(handshake_times)
            },
            "latency": {
                "avg_ms": statistics.mean(latency_times) if latency_times else 0.0,
                "min_ms": min(latency_times) if latency_times else 0.0,
                "max_ms": max(latency_times) if latency_times else 0.0,
                "samples": len(latency_times)
            }
        }
        
        aggregation = MetricsAggregation(
            start_time=actual_start_time,
            end_time=actual_end_time,
            total_reconnect_attempts=total_attempts,
            successful_reconnects=successful_reconnects,
            failed_reconnects=failed_reconnects,
            success_rate_percent=success_rate,
            average_reconnect_time_s=avg_reconnect_time,
            error_distribution=error_distribution,
            performance_summary=performance_summary,
            state_distribution=state_distribution
        )
        
        self.aggregations.append(aggregation)
        
        self.structured_logger.info(
            "Metrics aggregated",
            status=LogStatus.COMPLETED,
            time_range_s=actual_end_time - actual_start_time,
            snapshots_processed=len(filtered_snapshots),
            success_rate=success_rate,
            total_attempts=total_attempts
        )
        
        return aggregation
    
    def export_to_json(self, filepath: str, include_snapshots: bool = True,
                      include_aggregations: bool = True) -> None:
        """
        Export metrics to JSON format.
        
        Args:
            filepath: Path to save JSON file
            include_snapshots: Whether to include raw snapshots
            include_aggregations: Whether to include aggregations
        """
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat() + "Z",
            "collector_id": self.collector_id,
            "collection_interval_s": self.collection_interval,
            "total_snapshots": len(self.snapshots)
        }
        
        if include_snapshots:
            export_data["snapshots"] = [
                {
                    "timestamp": s.timestamp,
                    "datetime": datetime.fromtimestamp(s.timestamp).isoformat(),
                    "reconnect_metrics": s.reconnect_metrics,
                    "performance_metrics": s.performance_metrics,
                    "connection_state": s.connection_state,
                    "correlation_id": s.correlation_id
                }
                for s in self.snapshots
            ]
        
        if include_aggregations:
            export_data["aggregations"] = [
                {
                    "start_time": a.start_time,
                    "end_time": a.end_time,
                    "start_datetime": datetime.fromtimestamp(a.start_time).isoformat(),
                    "end_datetime": datetime.fromtimestamp(a.end_time).isoformat(),
                    "total_reconnect_attempts": a.total_reconnect_attempts,
                    "successful_reconnects": a.successful_reconnects,
                    "failed_reconnects": a.failed_reconnects,
                    "success_rate_percent": a.success_rate_percent,
                    "average_reconnect_time_s": a.average_reconnect_time_s,
                    "error_distribution": a.error_distribution,
                    "performance_summary": a.performance_summary,
                    "state_distribution": a.state_distribution
                }
                for a in self.aggregations
            ]
        
        try:
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            self.structured_logger.info(
                "Metrics exported to JSON",
                status=LogStatus.COMPLETED,
                filepath=filepath,
                snapshots_exported=len(self.snapshots) if include_snapshots else 0,
                aggregations_exported=len(self.aggregations) if include_aggregations else 0
            )
            
        except Exception as e:
            self.structured_logger.error(
                "Failed to export metrics to JSON",
                status=LogStatus.FAILED,
                filepath=filepath,
                error=e
            )
            raise
    
    def export_to_csv(self, filepath: str, data_type: str = "snapshots") -> None:
        """
        Export metrics to CSV format.
        
        Args:
            filepath: Path to save CSV file
            data_type: Type of data to export ("snapshots" or "aggregations")
        """
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                
                if data_type == "snapshots":
                    # CSV headers for snapshots
                    headers = [
                        "timestamp", "datetime", "connection_state", "correlation_id",
                        "reconnect_attempts", "successful_reconnects", "failed_reconnects",
                        "success_rate_percent", "average_reconnect_time_s",
                        "handshake_last_ms", "handshake_avg_ms", "handshake_violations",
                        "latency_last_ms", "latency_avg_ms", "latency_violations"
                    ]
                    writer.writerow(headers)
                    
                    # Write snapshot data
                    for snapshot in self.snapshots:
                        rm = snapshot.reconnect_metrics
                        pm = snapshot.performance_metrics
                        
                        row = [
                            snapshot.timestamp,
                            datetime.fromtimestamp(snapshot.timestamp).isoformat(),
                            snapshot.connection_state,
                            snapshot.correlation_id,
                            rm["reconnect_attempts"],
                            rm["successful_reconnects"],
                            rm["failed_reconnects"],
                            rm["success_rate_percent"],
                            rm["average_reconnect_time_s"],
                            pm["handshake"]["last_ms"] or 0,
                            pm["handshake"]["statistics"]["avg"],
                            pm["handshake"]["violations"],
                            pm["message_latency"]["last_ms"] or 0,
                            pm["message_latency"]["statistics"]["avg"],
                            pm["message_latency"]["violations"]
                        ]
                        writer.writerow(row)
                
                elif data_type == "aggregations":
                    # CSV headers for aggregations
                    headers = [
                        "start_time", "end_time", "start_datetime", "end_datetime",
                        "total_reconnect_attempts", "successful_reconnects", "failed_reconnects",
                        "success_rate_percent", "average_reconnect_time_s",
                        "handshake_avg_ms", "latency_avg_ms"
                    ]
                    writer.writerow(headers)
                    
                    # Write aggregation data
                    for agg in self.aggregations:
                        row = [
                            agg.start_time,
                            agg.end_time,
                            datetime.fromtimestamp(agg.start_time).isoformat(),
                            datetime.fromtimestamp(agg.end_time).isoformat(),
                            agg.total_reconnect_attempts,
                            agg.successful_reconnects,
                            agg.failed_reconnects,
                            agg.success_rate_percent,
                            agg.average_reconnect_time_s,
                            agg.performance_summary["handshake"]["avg_ms"],
                            agg.performance_summary["latency"]["avg_ms"]
                        ]
                        writer.writerow(row)
                
                else:
                    raise ValueError(f"Invalid data_type: {data_type}")
            
            self.structured_logger.info(
                "Metrics exported to CSV",
                status=LogStatus.COMPLETED,
                filepath=filepath,
                data_type=data_type,
                rows_exported=len(self.snapshots) if data_type == "snapshots" else len(self.aggregations)
            )
            
        except Exception as e:
            self.structured_logger.error(
                "Failed to export metrics to CSV",
                status=LogStatus.FAILED,
                filepath=filepath,
                data_type=data_type,
                error=e
            )
            raise
    
    def get_trend_analysis(self, metric_name: str, window_size: int = 10) -> Dict[str, Any]:
        """
        Analyze trends in a specific metric over time.
        
        Args:
            metric_name: Name of metric to analyze
            window_size: Size of moving average window
            
        Returns:
            Dictionary containing trend analysis
        """
        if len(self.snapshots) < window_size:
            return {"trend": "insufficient_data", "samples": len(self.snapshots)}
        
        # Extract metric values over time
        values = []
        timestamps = []
        
        for snapshot in self.snapshots:
            if metric_name == "success_rate":
                values.append(snapshot.reconnect_metrics["success_rate_percent"])
            elif metric_name == "reconnect_time":
                values.append(snapshot.reconnect_metrics["average_reconnect_time_s"])
            elif metric_name == "handshake_time":
                values.append(snapshot.performance_metrics["handshake"]["statistics"]["avg"])
            elif metric_name == "message_latency":
                values.append(snapshot.performance_metrics["message_latency"]["statistics"]["avg"])
            else:
                raise ValueError(f"Unknown metric: {metric_name}")
            
            timestamps.append(snapshot.timestamp)
        
        # Calculate moving averages
        moving_averages = []
        for i in range(window_size - 1, len(values)):
            window = values[i - window_size + 1:i + 1]
            moving_averages.append(statistics.mean(window))
        
        # Determine trend
        if len(moving_averages) < 2:
            trend = "stable"
        else:
            recent_avg = statistics.mean(moving_averages[-min(5, len(moving_averages)):])
            older_avg = statistics.mean(moving_averages[:min(5, len(moving_averages))])
            
            if recent_avg > older_avg * 1.1:
                trend = "increasing"
            elif recent_avg < older_avg * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        
        return {
            "metric_name": metric_name,
            "trend": trend,
            "samples": len(values),
            "current_value": values[-1] if values else 0,
            "min_value": min(values) if values else 0,
            "max_value": max(values) if values else 0,
            "avg_value": statistics.mean(values) if values else 0,
            "moving_averages": moving_averages,
            "window_size": window_size
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get real-time dashboard data for display.
        
        Returns:
            Dictionary containing dashboard metrics
        """
        if not self.snapshots:
            return {"status": "no_data", "message": "No metrics collected yet"}
        
        latest_snapshot = self.snapshots[-1]
        rm = latest_snapshot.reconnect_metrics
        pm = latest_snapshot.performance_metrics
        
        # Calculate recent trends
        recent_snapshots = list(self.snapshots)[-10:]  # Last 10 snapshots
        
        dashboard_data = {
            "status": "active",
            "last_updated": datetime.fromtimestamp(latest_snapshot.timestamp).isoformat(),
            "connection_state": latest_snapshot.connection_state,
            "reconnect_summary": {
                "total_attempts": rm["reconnect_attempts"],
                "success_rate_percent": rm["success_rate_percent"],
                "recent_failures": len([s for s in recent_snapshots 
                                      if s.reconnect_metrics["failed_reconnects"] > 0]),
                "average_reconnect_time_s": rm["average_reconnect_time_s"]
            },
            "performance_summary": {
                "handshake_healthy": pm["handshake"]["healthy"],
                "latency_healthy": pm["message_latency"]["healthy"],
                "handshake_last_ms": pm["handshake"]["last_ms"],
                "latency_last_ms": pm["message_latency"]["last_ms"],
                "handshake_violations": pm["handshake"]["violations"],
                "latency_violations": pm["message_latency"]["violations"]
            },
            "trends": {
                "success_rate": self.get_trend_analysis("success_rate", min(5, len(self.snapshots))),
                "handshake_time": self.get_trend_analysis("handshake_time", min(5, len(self.snapshots)))
            },
            "collection_info": {
                "total_snapshots": len(self.snapshots),
                "collection_interval_s": self.collection_interval,
                "collecting": self.collecting
            }
        }
        
        return dashboard_data
    
    def reset_metrics(self) -> None:
        """Reset all collected metrics and aggregations."""
        self.snapshots.clear()
        self.aggregations.clear()
        self.last_collection_time = None
        
        self.structured_logger.info(
            "Metrics collector reset",
            status=LogStatus.COMPLETED,
            reset_timestamp=time.time()
        )


# Convenience functions for easy integration
def create_metrics_collector(max_snapshots: int = 1000, 
                           collection_interval: float = 5.0) -> MetricsCollector:
    """
    Create a new metrics collector instance.
    
    Args:
        max_snapshots: Maximum number of snapshots to keep
        collection_interval: Collection interval in seconds
        
    Returns:
        MetricsCollector instance
    """
    return MetricsCollector(max_snapshots, collection_interval)


async def collect_metrics_for_duration(websocket_client, duration_s: float, 
                                     collection_interval: float = 1.0) -> MetricsCollector:
    """
    Collect metrics for a specific duration.
    
    Args:
        websocket_client: WebSocketDemoClient to monitor
        duration_s: Duration to collect metrics for
        collection_interval: Collection interval in seconds
        
    Returns:
        MetricsCollector with collected data
    """
    collector = MetricsCollector(collection_interval=collection_interval)
    collector.start_collection(websocket_client)
    
    try:
        await asyncio.sleep(duration_s)
    finally:
        await collector.stop_collection()
    
    return collector


if __name__ == "__main__":
    # Example usage
    print("Metrics Collector for WebSocket Demo Client")
    print("This module provides comprehensive metrics collection and analysis.")
    print("Import and use with WebSocketDemoClient for reconnect behavior analysis.")