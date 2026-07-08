"""
WebSocket Manager
==================
WebSocket 기반 실시간 파이프라인 모니터링 및 이벤트 알림.
"""

import json
import asyncio
import time
from typing import Optional, Set, Dict, Any
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect


# ──────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────


@dataclass
class WSMessage:
    """WebSocket message type."""
    type: str  # pipeline_update, stage_update, error, heartbeat, log
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def to_json(self) -> str:
        if not self.timestamp:
            self.timestamp = time.time()
        return json.dumps({
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
        })

    @classmethod
    def pipeline_update(cls, pipeline_id: str, status: str, progress: float, **kwargs) -> "WSMessage":
        return cls(
            type="pipeline_update",
            data={"pipeline_id": pipeline_id, "status": status, "progress": progress, **kwargs},
        )

    @classmethod
    def stage_update(cls, pipeline_id: str, stage_name: str, status: str, **kwargs) -> "WSMessage":
        return cls(
            type="stage_update",
            data={"pipeline_id": pipeline_id, "stage_name": stage_name, "status": status, **kwargs},
        )

    @classmethod
    def error(cls, message: str, code: str = "internal_error") -> "WSMessage":
        return cls(type="error", data={"message": message, "code": code})

    @classmethod
    def heartbeat(cls) -> "WSMessage":
        return cls(type="heartbeat", data={})


# ──────────────────────────────────────────────────────────
# Connection Manager
# ──────────────────────────────────────────────────────────


class ConnectionManager:
    """
    Manages WebSocket connections with automatic cleanup.
    Supports broadcasting and targeted messages.
    """

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._subscriptions: Dict[str, Set[WebSocket]] = {}
        self._connection_metadata: Dict[WebSocket, Dict] = {}
        self._active = False
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket, metadata: Optional[Dict] = None) -> None:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            metadata: Optional client metadata
        """
        await websocket.accept()
        self._connections.add(websocket)
        self._connection_metadata[websocket] = metadata or {}
        self._start_heartbeat()

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self._connections.discard(websocket)
        self._connection_metadata.pop(websocket, None)

        # Remove from all subscriptions
        for topic, subscribers in self._subscriptions.items():
            subscribers.discard(websocket)

        if not self._connections and self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._active = False

    async def send_message(self, websocket: WebSocket, message: WSMessage) -> bool:
        """Send a message to a specific client."""
        try:
            await websocket.send_text(message.to_json())
            return True
        except Exception:
            await self.disconnect(websocket)
            return False

    async def broadcast(self, message: WSMessage) -> int:
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message to broadcast

        Returns:
            Number of clients message was sent to
        """
        dead_connections = set()
        for websocket in self._connections:
            try:
                await websocket.send_text(message.to_json())
            except Exception:
                dead_connections.add(websocket)

        for dead in dead_connections:
            await self.disconnect(dead)

        return len(self._connections) - len(dead_connections)

    async def publish(self, topic: str, message: WSMessage) -> int:
        """
        Publish a message to all subscribers of a topic.

        Args:
            topic: Topic name (e.g., pipeline_id)
            message: Message to publish

        Returns:
            Number of subscribers message was sent to
        """
        subscribers = self._subscriptions.get(topic, set())
        count = 0
        dead = set()

        for websocket in subscribers:
            try:
                await websocket.send_text(message.to_json())
                count += 1
            except Exception:
                dead.add(websocket)

        for d in dead:
            await self.disconnect(d)
            subscribers.discard(d)

        return count

    async def subscribe(self, websocket: WebSocket, topic: str) -> None:
        """Subscribe a client to a topic."""
        if topic not in self._subscriptions:
            self._subscriptions[topic] = set()
        self._subscriptions[topic].add(websocket)

    async def unsubscribe(self, websocket: WebSocket, topic: str) -> None:
        """Unsubscribe a client from a topic."""
        subscribers = self._subscriptions.get(topic)
        if subscribers:
            subscribers.discard(websocket)

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    @property
    def active_topics(self) -> Dict[str, int]:
        return {topic: len(subs) for topic, subs in self._subscriptions.items()}

    def _start_heartbeat(self) -> None:
        """Start background heartbeat task."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._active = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        """Send heartbeat to all connections every 30 seconds."""
        while self._active and self._connections:
            await asyncio.sleep(30)
            if self._connections:
                await self.broadcast(WSMessage.heartbeat())


# ──────────────────────────────────────────────────────────
# WebSocket Manager
# ──────────────────────────────────────────────────────────


class WebSocketManager:
    """
    High-level WebSocket manager integrating with FastAPI.

    Usage:
        manager = WebSocketManager()

        @app.websocket("/api/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await manager.handle_connection(websocket)
    """

    def __init__(self):
        self.connection_manager = ConnectionManager()

    async def handle_connection(self, websocket: WebSocket) -> None:
        """
        Handle a WebSocket connection lifecycle.

        Accepts the connection, processes messages (subscribe, unsubscribe),
        and handles disconnection.

        Args:
            websocket: WebSocket connection
        """
        await self.connection_manager.connect(websocket, {"connected_at": time.time()})

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    await self._handle_message(websocket, message)
                except json.JSONDecodeError:
                    await self.connection_manager.send_message(
                        websocket,
                        WSMessage.error("Invalid JSON message", "invalid_format"),
                    )
        except WebSocketDisconnect:
            await self.connection_manager.disconnect(websocket)

    async def _handle_message(self, websocket: WebSocket, message: Dict) -> None:
        """
        Handle an incoming WebSocket message.

        Supported message types:
            - {"type": "subscribe", "topic": "pipeline_{id}"}
            - {"type": "unsubscribe", "topic": "pipeline_{id}"}
            - {"type": "ping"} → pong
        """
        msg_type = message.get("type")

        if msg_type == "subscribe":
            topic = message.get("topic")
            if topic:
                await self.connection_manager.subscribe(websocket, topic)
                await self.connection_manager.send_message(
                    websocket,
                    WSMessage(type="subscribed", data={"topic": topic}),
                )

        elif msg_type == "unsubscribe":
            topic = message.get("topic")
            if topic:
                await self.connection_manager.unsubscribe(websocket, topic)

        elif msg_type == "ping":
            await self.connection_manager.send_message(
                websocket,
                WSMessage(type="pong", data={}),
            )

    async def broadcast_pipeline_update(
        self,
        pipeline_id: str,
        status: str,
        progress: float,
        **kwargs,
    ) -> None:
        """Broadcast pipeline status update."""
        message = WSMessage.pipeline_update(pipeline_id, status, progress, **kwargs)

        # Broadcast to all + publish to pipeline subscribers
        await self.connection_manager.broadcast(message)
        await self.connection_manager.publish(f"pipeline_{pipeline_id}", message)

    async def broadcast_stage_update(
        self,
        pipeline_id: str,
        stage_name: str,
        status: str,
        **kwargs,
    ) -> None:
        """Broadcast stage status update."""
        message = WSMessage.stage_update(pipeline_id, stage_name, status, **kwargs)
        await self.connection_manager.broadcast(message)
        await self.connection_manager.publish(f"pipeline_{pipeline_id}", message)

    async def send_error(self, websocket: WebSocket, error_message: str) -> None:
        """Send an error message to a specific client."""
        await self.connection_manager.send_message(
            websocket,
            WSMessage.error(error_message),
        )

    @property
    def stats(self) -> Dict:
        """Get connection statistics."""
        return {
            "active_connections": self.connection_manager.active_connections,
            "topics": self.connection_manager.active_topics,
        }
