"""
Demo WebSocket Client Package

This package provides a demonstration WebSocket client for the Clarity Local Runner
WebSocket devteam endpoint with linear reconnect logic following ADD Profile C.
"""

__version__ = "1.0.0"
__author__ = "Clarity Local Runner Team"

from .websocket_demo_client import WebSocketDemoClient

__all__ = ["WebSocketDemoClient"]