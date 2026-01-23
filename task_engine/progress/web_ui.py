"""
Web UI integration for progress tracking and task control.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from aiohttp import web, WSMsgType
import aiohttp_cors

from . import ProgressTracker, ProgressCallback, ProgressUpdate, TaskController
from ..task import Task, TaskState

logger = logging.getLogger(__name__)


class WebSocketProgressCallback(ProgressCallback):
    """
    WebSocket-based progress callback for real-time UI updates.
    """

    def __init__(self):
        self._websockets: List[web.WebSocketResponse] = []
        self._lock = asyncio.Lock()

    async def add_websocket(self, ws: web.WebSocketResponse):
        """
        Add a WebSocket connection.

        Args:
            ws: WebSocket response
        """
        async with self._lock:
            self._websockets.append(ws)

    async def remove_websocket(self, ws: web.WebSocketResponse):
        """
        Remove a WebSocket connection.

        Args:
            ws: WebSocket response
        """
        async with self._lock:
            self._websockets.remove(ws)

    async def on_progress_update(self, update: ProgressUpdate):
        """
        Handle progress update by broadcasting to WebSocket clients.

        Args:
            update: Progress update
        """
        message = {
            "type": "progress_update",
            "task_id": update.task_id,
            "timestamp": update.timestamp.isoformat(),
            "percentage": update.percentage,
            "stage": update.stage,
            "message": update.message,
            "eta_seconds": update.eta_seconds,
            "current_step": update.current_step,
            "total_steps": update.total_steps,
            "metadata": update.metadata
        }

        await self._broadcast(message)

    async def on_task_started(self, task: Task):
        """
        Handle task started by broadcasting to WebSocket clients.

        Args:
            task: Task that started
        """
        message = {
            "type": "task_started",
            "task_id": task.id,
            "task_type": task.task_type,
            "priority": task.priority,
            "timestamp": datetime.now().isoformat()
        }

        await self._broadcast(message)

    async def on_task_completed(self, task: Task):
        """
        Handle task completed by broadcasting to WebSocket clients.

        Args:
            task: Task that completed
        """
        message = {
            "type": "task_completed",
            "task_id": task.id,
            "state": task.state.value,
            "result": task.result,
            "error": str(task.error) if task.error else None,
            "timestamp": datetime.now().isoformat()
        }

        await self._broadcast(message)

    async def _broadcast(self, message: Dict[str, Any]):
        """
        Broadcast message to all connected WebSocket clients.

        Args:
            message: Message to broadcast
        """
        async with self._lock:
            disconnected = []
            for ws in self._websockets:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to WebSocket: {e}")
                    disconnected.append(ws)

            # Clean up disconnected clients
            for ws in disconnected:
                self._websockets.remove(ws)


class ProgressWebAPI:
    """
    Web API for progress tracking and task control.
    """

    def __init__(self, progress_tracker: ProgressTracker, task_controller: TaskController,
                 host: str = "localhost", port: int = 8080):
        """
        Initialize web API.

        Args:
            progress_tracker: Progress tracker instance
            task_controller: Task controller instance
            host: Host to bind to
            port: Port to bind to
        """
        self.progress_tracker = progress_tracker
        self.task_controller = task_controller
        self.host = host
        self.port = port

        self.ws_callback = WebSocketProgressCallback()
        self.progress_tracker.add_callback(self.ws_callback)

        self.app = web.Application()
        self._setup_routes()
        self._setup_cors()

        self.runner = None
        self.site = None

    def _setup_routes(self):
        """Set up API routes."""
        self.app.router.add_get("/api/tasks", self.get_tasks)
        self.app.router.add_get("/api/tasks/{task_id}", self.get_task)
        self.app.router.add_get("/api/tasks/{task_id}/progress", self.get_task_progress)
        self.app.router.add_post("/api/tasks/{task_id}/cancel", self.cancel_task)
        self.app.router.add_get("/ws/progress", self.websocket_handler)

        # Static files for basic UI
        self.app.router.add_static("/", "static")

    def _setup_cors(self):
        """Set up CORS for web API."""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

        # Apply CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)

    async def get_tasks(self, request: web.Request) -> web.Response:
        """
        Get all tasks.

        Args:
            request: HTTP request

        Returns:
            JSON response with tasks
        """
        # This would need to be implemented to get tasks from the task manager
        # For now, return empty list
        tasks = []

        return web.json_response({
            "tasks": tasks,
            "count": len(tasks)
        })

    async def get_task(self, request: web.Request) -> web.Response:
        """
        Get a specific task.

        Args:
            request: HTTP request

        Returns:
            JSON response with task details
        """
        task_id = request.match_info.get("task_id")

        # This would need to be implemented to get task from storage
        # For now, return not found
        return web.json_response({"error": "Task not found"}, status=404)

    async def get_task_progress(self, request: web.Request) -> web.Response:
        """
        Get progress for a specific task.

        Args:
            request: HTTP request

        Returns:
            JSON response with progress
        """
        task_id = request.match_info.get("task_id")

        progress = self.progress_tracker.get_progress(task_id)
        if progress:
            return web.json_response({
                "task_id": task_id,
                "percentage": progress.percentage,
                "stage": progress.stage,
                "message": progress.message,
                "eta_seconds": progress.eta_seconds,
                "current_step": progress.current_step,
                "total_steps": progress.total_steps
            })
        else:
            return web.json_response({"error": "Progress not found"}, status=404)

    async def cancel_task(self, request: web.Request) -> web.Response:
        """
        Cancel a task.

        Args:
            request: HTTP request

        Returns:
            JSON response
        """
        task_id = request.match_info.get("task_id")

        cancelled = self.task_controller.cancel_task(task_id)
        if cancelled:
            return web.json_response({"message": f"Task {task_id} cancelled"})
        else:
            return web.json_response({"error": "Task not found or already completed"}, status=404)

    async def websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """
        Handle WebSocket connections for real-time progress updates.

        Args:
            request: HTTP request

        Returns:
            WebSocket response
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        logger.info("WebSocket connection opened")

        # Add to callback
        await self.ws_callback.add_websocket(ws)

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        # Handle incoming messages if needed
                        logger.debug(f"Received WebSocket message: {data}")
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received on WebSocket")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await self.ws_callback.remove_websocket(ws)
            logger.info("WebSocket connection closed")

        return ws

    async def start(self):
        """Start the web server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        logger.info(f"Progress Web API started on http://{self.host}:{self.port}")

    async def stop(self):
        """Stop the web server."""
        if self.site:
            await self.site.stop()

        if self.runner:
            await self.runner.cleanup()

        logger.info("Progress Web API stopped")


class ProgressDashboard:
    """
    Simple HTML dashboard for monitoring task progress.
    """

    @staticmethod
    def get_dashboard_html() -> str:
        """
        Get HTML for the progress dashboard.

        Returns:
            HTML string
        """
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comfy Gimpy Studio - Task Progress</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .task-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #45a049);
            width: 0%;
            transition: width 0.3s ease;
        }
        .task-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .task-status {
            padding: 4px 8px;
            border-radius: 4px;
            color: white;
            font-size: 12px;
        }
        .status-pending { background-color: #ff9800; }
        .status-running { background-color: #2196F3; }
        .status-completed { background-color: #4CAF50; }
        .status-failed { background-color: #f44336; }
        .status-cancelled { background-color: #9e9e9e; }
        .cancel-btn {
            background-color: #f44336;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
        }
        .cancel-btn:hover {
            background-color: #d32f2f;
        }
        .message {
            color: #666;
            font-style: italic;
        }
        .eta {
            color: #2196F3;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Comfy Gimpy Studio - Task Progress Dashboard</h1>
            <p>Real-time monitoring of async task execution</p>
        </div>

        <div id="tasks-container">
            <div class="task-card">
                <div class="task-info">
                    <h3>Connecting to progress service...</h3>
                    <span class="task-status status-pending">Connecting</span>
                </div>
            </div>
        </div>
    </div>

    <script>
        let ws;
        const tasksContainer = document.getElementById('tasks-container');
        const taskElements = new Map();

        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8080/ws/progress');

            ws.onopen = function(event) {
                console.log('Connected to progress service');
                tasksContainer.innerHTML = '<div class="task-card"><div class="task-info"><h3>Connected - Waiting for tasks...</h3><span class="task-status status-pending">Connected</span></div></div>';
            };

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };

            ws.onclose = function(event) {
                console.log('Disconnected from progress service');
                tasksContainer.innerHTML = '<div class="task-card"><div class="task-info"><h3>Disconnected - Retrying...</h3><span class="task-status status-pending">Reconnecting</span></div></div>';
                setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }

        function handleMessage(data) {
            switch(data.type) {
                case 'task_started':
                    createTaskElement(data.task_id, data);
                    break;
                case 'progress_update':
                    updateTaskProgress(data);
                    break;
                case 'task_completed':
                    updateTaskCompletion(data);
                    break;
            }
        }

        function createTaskElement(taskId, data) {
            if (taskElements.has(taskId)) return;

            const taskCard = document.createElement('div');
            taskCard.className = 'task-card';
            taskCard.id = `task-${taskId}`;

            taskCard.innerHTML = `
                <div class="task-info">
                    <h3>Task ${taskId}</h3>
                    <div>
                        <span class="task-status status-running">Running</span>
                        <button class="cancel-btn" onclick="cancelTask('${taskId}')">Cancel</button>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-${taskId}"></div>
                </div>
                <div class="message" id="message-${taskId}">Initializing...</div>
                <div class="eta" id="eta-${taskId}"></div>
            `;

            tasksContainer.appendChild(taskCard);
            taskElements.set(taskId, taskCard);
        }

        function updateTaskProgress(data) {
            const progressFill = document.getElementById(`progress-${data.task_id}`);
            const messageEl = document.getElementById(`message-${data.task_id}`);
            const etaEl = document.getElementById(`eta-${data.task_id}`);

            if (progressFill) {
                progressFill.style.width = `${data.percentage}%`;
            }

            if (messageEl) {
                let message = data.stage;
                if (data.message) {
                    message += ` - ${data.message}`;
                }
                if (data.current_step && data.total_steps) {
                    message += ` (${data.current_step}/${data.total_steps})`;
                }
                messageEl.textContent = message;
            }

            if (etaEl && data.eta_seconds) {
                const eta = formatETA(data.eta_seconds);
                etaEl.textContent = `ETA: ${eta}`;
            }
        }

        function updateTaskCompletion(data) {
            const taskCard = document.getElementById(`task-${data.task_id}`);
            const statusEl = taskCard.querySelector('.task-status');
            const cancelBtn = taskCard.querySelector('.cancel-btn');

            if (statusEl) {
                statusEl.className = `task-status status-${data.state.toLowerCase()}`;
                statusEl.textContent = data.state.charAt(0).toUpperCase() + data.state.slice(1);
            }

            if (cancelBtn) {
                cancelBtn.style.display = 'none';
            }

            const messageEl = document.getElementById(`message-${data.task_id}`);
            if (messageEl) {
                if (data.error) {
                    messageEl.textContent = `Error: ${data.error}`;
                    messageEl.style.color = '#f44336';
                } else {
                    messageEl.textContent = 'Completed successfully';
                    messageEl.style.color = '#4CAF50';
                }
            }
        }

        function cancelTask(taskId) {
            fetch(`/api/tasks/${taskId}/cancel`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    console.log('Cancel response:', data);
                })
                .catch(error => {
                    console.error('Cancel error:', error);
                });
        }

        function formatETA(seconds) {
            if (seconds < 60) {
                return `${Math.round(seconds)}s`;
            } else if (seconds < 3600) {
                const minutes = Math.floor(seconds / 60);
                const remainingSeconds = Math.round(seconds % 60);
                return `${minutes}m ${remainingSeconds}s`;
            } else {
                const hours = Math.floor(seconds / 3600);
                const minutes = Math.floor((seconds % 3600) / 60);
                return `${hours}h ${minutes}m`;
            }
        }

        // Connect on page load
        connectWebSocket();
    </script>
</body>
</html>
        """

    @staticmethod
    def create_static_files():
        """Create static files for the dashboard."""
        import os

        # Create static directory if it doesn't exist
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        os.makedirs(static_dir, exist_ok=True)

        # Write dashboard HTML
        dashboard_path = os.path.join(static_dir, "index.html")
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(ProgressDashboard.get_dashboard_html())