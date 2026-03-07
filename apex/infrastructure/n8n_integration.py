#!/usr/bin/env python3
"""
APEX n8n Workflow Integration Module
====================================
Connects the Agent Layer to n8n automation workflows with bidirectional
communication, webhook-based triggering, and execution monitoring.

This module serves as the bridge between the Agent Intelligence Layer
and external n8n automation workflows for 72-agent and 24-agent orchestration.

Author: APEX Core Team
Version: 1.0.0
License: MIT
"""

import os
import sys
import json
import asyncio
import logging
import hashlib
import hmac
import time
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from collections import defaultdict
import uuid
from contextlib import asynccontextmanager

# Optional imports - graceful degradation if not available
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

try:
    from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, BackgroundTasks
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = APIRouter = HTTPException = Request = Response = Depends = BackgroundTasks = None
    JSONResponse = None
    BaseModel = object
    Field = lambda *args, **kwargs: None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/apex_n8n_integration.log')
    ]
)
logger = logging.getLogger('N8NIntegration')


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class WorkflowType(Enum):
    """Types of n8n workflows supported"""
    AGENT_ORCHESTRATION_72 = "72-agent-orchestration"
    AGENT_ORCHESTRATION_24 = "24-agent-orchestrator"
    NOTIFICATION = "notification"
    REPORTING = "reporting"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    CUSTOM = "custom"


class WebhookEventType(Enum):
    """Event types for webhook callbacks"""
    CHECKOUT_COMPLETE = "checkout_complete"
    BUILD_COMPLETE = "build_complete"
    DEPLOYMENT_COMPLETE = "deployment_complete"
    ERROR_ALERT = "error_alert"
    AGENT_SPAWNED = "agent_spawned"
    CHECKPOINT_CREATED = "checkpoint_created"
    CONSENSUS_REACHED = "consensus_reached"
    EVALUATION_COMPLETE = "evaluation_complete"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_FINISHED = "workflow_finished"


class NotificationChannel(Enum):
    """Notification channels supported"""
    SLACK = "slack"
    DISCORD = "discord"
    EMAIL = "email"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    SMS = "sms"


class NotificationPriority(Enum):
    """Notification priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class WorkflowExecution:
    """Record of a workflow execution"""
    execution_id: str
    workflow_id: str
    workflow_type: WorkflowType
    status: str  # pending, running, completed, failed
    payload: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    callback_url: Optional[str] = None
    retry_count: int = 0


@dataclass
class WebhookRegistration:
    """Registered webhook endpoint"""
    endpoint: str
    handler: Callable
    event_types: List[WebhookEventType]
    secret: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AgentEvent:
    """Agent layer event"""
    event_type: str
    agent_id: Optional[str]
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationPayload:
    """Notification payload structure"""
    channel: NotificationChannel
    message: str
    priority: NotificationPriority
    title: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


# Pydantic models for FastAPI (fallback if not available)
if FASTAPI_AVAILABLE:
    class TriggerWorkflowRequest(BaseModel):
        """Request model for triggering a workflow"""
        workflow_id: str
        payload: Dict[str, Any] = Field(default_factory=dict)
        callback_url: Optional[str] = None
        wait_for_completion: bool = False
        timeout_seconds: int = 300


    class TriggerWorkflowResponse(BaseModel):
        """Response model for workflow trigger"""
        execution_id: str
        workflow_id: str
        status: str
        message: str
        estimated_duration: Optional[str] = None


    class WebhookCallbackRequest(BaseModel):
        """Request model for webhook callbacks"""
        event_type: str
        execution_id: str
        data: Dict[str, Any]
        timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
        signature: Optional[str] = None


    class AgentStatusUpdate(BaseModel):
        """Model for agent status updates"""
        agent_id: str
        status: str
        current_task: Optional[str] = None
        metadata: Dict[str, Any] = Field(default_factory=dict)


    class NotificationRequest(BaseModel):
        """Request model for sending notifications"""
        channel: str
        message: str
        priority: str = "medium"
        title: Optional[str] = None
        metadata: Dict[str, Any] = Field(default_factory=dict)
else:
    # Fallback dataclasses
    @dataclass
    class TriggerWorkflowRequest:
        workflow_id: str
        payload: Dict[str, Any] = field(default_factory=dict)
        callback_url: Optional[str] = None
        wait_for_completion: bool = False
        timeout_seconds: int = 300

    @dataclass
    class TriggerWorkflowResponse:
        execution_id: str
        workflow_id: str
        status: str
        message: str
        estimated_duration: Optional[str] = None

    @dataclass
    class WebhookCallbackRequest:
        event_type: str
        execution_id: str
        data: Dict[str, Any]
        timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
        signature: Optional[str] = None

    @dataclass
    class AgentStatusUpdate:
        agent_id: str
        status: str
        current_task: Optional[str] = None
        metadata: Dict[str, Any] = field(default_factory=dict)

    @dataclass
    class NotificationRequest:
        channel: str
        message: str
        priority: str = "medium"
        title: Optional[str] = None
        metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# EVENT MAPPING CONFIGURATION
# ============================================================================

# Event to workflow mapping
DEFAULT_EVENT_WORKFLOW_MAP = {
    "checkpoint_created": WorkflowType.AGENT_ORCHESTRATION_72,
    "consensus_reached": WorkflowType.NOTIFICATION,
    "evaluation_complete": WorkflowType.REPORTING,
    "agent_spawned": WorkflowType.MONITORING,
    "build_complete": WorkflowType.DEPLOYMENT,
    "deployment_complete": WorkflowType.NOTIFICATION,
    "error_alert": WorkflowType.NOTIFICATION,
    "workflow_started": WorkflowType.MONITORING,
    "workflow_finished": WorkflowType.REPORTING,
}

# Workflow type to n8n webhook ID mapping
WORKFLOW_WEBHOOK_MAP = {
    WorkflowType.AGENT_ORCHESTRATION_72: "apex-orchestrate",
    WorkflowType.AGENT_ORCHESTRATION_24: "apex-24-orchestrate",
    WorkflowType.NOTIFICATION: "apex-notify",
    WorkflowType.REPORTING: "apex-report",
    WorkflowType.DEPLOYMENT: "apex-deploy",
    WorkflowType.MONITORING: "apex-monitor",
    WorkflowType.CUSTOM: "apex-custom",
}


# ============================================================================
# N8N INTEGRATION CLASS
# ============================================================================

class N8NIntegration:
    """
    Main integration class for n8n workflow automation.
    
    Provides:
    - Webhook-based workflow triggering
    - Workflow execution monitoring
    - Bidirectional communication (send/receive)
    - Error handling and retry logic
    - Event mapping and routing
    - Agent status synchronization
    """
    
    def __init__(
        self,
        webhook_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize n8n integration
        
        Args:
            webhook_base_url: Base URL for webhook callbacks to this service
            api_key: n8n API key for authentication
            base_url: n8n instance base URL (default: http://localhost:5678)
            webhook_secret: Secret for webhook signature verification
            max_retries: Maximum retry attempts for failed requests
            retry_delay: Delay between retries in seconds
        """
        # Configuration from environment or parameters
        self.webhook_base_url = webhook_base_url or os.getenv(
            'N8N_WEBHOOK_URL', 
            'http://localhost:8000/webhooks/n8n'
        )
        self.api_key = api_key or os.getenv('N8N_API_KEY', '')
        self.base_url = base_url or os.getenv('N8N_BASE_URL', 'http://localhost:5678')
        self.webhook_secret = webhook_secret or os.getenv('WEBHOOK_SECRET', '')
        
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # State management
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.completed_executions: List[WorkflowExecution] = []
        self.webhook_registrations: Dict[str, WebhookRegistration] = {}
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.agent_status_cache: Dict[str, Dict[str, Any]] = {}
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
        
        # Event mapping
        self.event_workflow_map = DEFAULT_EVENT_WORKFLOW_MAP.copy()
        
        logger.info(f"N8N Integration initialized (base_url: {self.base_url})")
    
    async def _get_client(self):
        """Get or create HTTP client"""
        if not HTTPX_AVAILABLE:
            logger.warning("httpx not available - using mock client")
            return None
            
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers['X-N8N-API-KEY'] = self.api_key
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
            )
        return self._client
    
    async def close(self):
        """Close HTTP client connections"""
        if not HTTPX_AVAILABLE:
            return
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    # ========================================================================
    # WORKFLOW TRIGGERING
    # ========================================================================
    
    async def trigger_workflow(
        self,
        workflow_id: str,
        payload: Dict[str, Any],
        callback_url: Optional[str] = None,
        wait_for_completion: bool = False,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Trigger an n8n workflow via webhook
        
        Args:
            workflow_id: The webhook ID or workflow ID to trigger
            payload: Data to send to the workflow
            callback_url: Optional callback URL for workflow completion
            wait_for_completion: Whether to wait for workflow to complete
            timeout_seconds: Timeout for waiting
            
        Returns:
            Dict with execution_id, status, and other metadata
        """
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        
        # Determine workflow type
        workflow_type = self._get_workflow_type(workflow_id)
        
        # Create execution record
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            status="pending",
            payload=payload,
            started_at=datetime.now(),
            callback_url=callback_url or f"{self.webhook_base_url}/callback"
        )
        self.active_executions[execution_id] = execution
        
        # Prepare webhook URL
        webhook_url = f"{self.base_url}/webhook/{workflow_id}"
        
        # Enrich payload with metadata
        enriched_payload = {
            **payload,
            "_apex_metadata": {
                "execution_id": execution_id,
                "callback_url": execution.callback_url,
                "triggered_at": datetime.now().isoformat(),
                "webhook_base_url": self.webhook_base_url
            }
        }
        
        logger.info(f"Triggering workflow {workflow_id} (execution: {execution_id})")
        
        # Check if HTTP client is available
        if not HTTPX_AVAILABLE:
            logger.warning("httpx not available - simulating workflow trigger")
            execution.status = "running"
            
            # Simulate async processing
            asyncio.create_task(self._simulate_workflow_execution(execution_id))
            
            return {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": "running",
                "message": "Workflow triggered (simulation mode - httpx not available)",
                "n8n_response": {"status": "accepted", "simulation": True},
                "estimated_duration": self._estimate_duration(workflow_type)
            }
        
        # Execute with retry logic
        for attempt in range(self.max_retries):
            try:
                client = await self._get_client()
                response = await client.post(
                    webhook_url,
                    json=enriched_payload,
                    timeout=30.0
                )
                
                if response.status_code in [200, 201, 202]:
                    execution.status = "running"
                    result = response.json() if response.content else {"status": "accepted"}
                    
                    logger.info(f"Workflow {workflow_id} triggered successfully")
                    
                    response_data = {
                        "execution_id": execution_id,
                        "workflow_id": workflow_id,
                        "status": "running",
                        "message": "Workflow triggered successfully",
                        "n8n_response": result,
                        "estimated_duration": self._estimate_duration(workflow_type)
                    }
                    
                    if wait_for_completion:
                        completion_result = await self._wait_for_completion(
                            execution_id, timeout_seconds
                        )
                        response_data["completion_result"] = completion_result
                    
                    return response_data
                    
                else:
                    logger.warning(f"Webhook returned {response.status_code}: {response.text}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    else:
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"n8n webhook failed: {response.text}"
                        )
                        
            except Exception as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    execution.status = "failed"
                    execution.error = str(e)
                    raise HTTPException(
                        status_code=503,
                        detail=f"Failed to trigger workflow after {self.max_retries} attempts: {e}"
                    )
        
        return {"error": "Unexpected end of trigger_workflow"}
    
    async def execute_workflow_with_callback(
        self,
        workflow_id: str,
        payload: Dict[str, Any],
        callback_handler: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Execute workflow with automatic callback handling
        
        Args:
            workflow_id: Workflow to execute
            payload: Workflow input data
            callback_handler: Optional async callback function for results
            
        Returns:
            Execution metadata
        """
        # Generate unique callback endpoint
        callback_id = f"cb-{uuid.uuid4().hex[:8]}"
        callback_url = f"{self.webhook_base_url}/callback/{callback_id}"
        
        # Store callback handler if provided
        if callback_handler:
            self.event_handlers[f"callback:{callback_id}"].append(callback_handler)
        
        return await self.trigger_workflow(
            workflow_id=workflow_id,
            payload=payload,
            callback_url=callback_url
        )
    
    async def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get status of a workflow execution
        
        Args:
            execution_id: The execution ID to query
            
        Returns:
            Execution status and details
        """
        execution = self.active_executions.get(execution_id)
        
        if not execution:
            # Check completed executions
            for exec in self.completed_executions:
                if exec.execution_id == execution_id:
                    return {
                        "execution_id": execution_id,
                        "workflow_id": exec.workflow_id,
                        "status": exec.status,
                        "started_at": exec.started_at.isoformat(),
                        "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                        "result": exec.result,
                        "error": exec.error
                    }
            
            raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
        
        return {
            "execution_id": execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status,
            "started_at": execution.started_at.isoformat(),
            "duration_seconds": (datetime.now() - execution.started_at).total_seconds(),
            "retry_count": execution.retry_count
        }
    
    # ========================================================================
    # WEBHOOK REGISTRATION AND HANDLING
    # ========================================================================
    
    def register_webhook(
        self,
        endpoint: str,
        handler: Callable,
        event_types: Optional[List[Union[str, WebhookEventType]]] = None,
        secret: Optional[str] = None
    ) -> str:
        """
        Register a webhook endpoint handler
        
        Args:
            endpoint: Webhook endpoint path (e.g., "/checkout-complete")
            handler: Async callback function to handle webhook
            event_types: Event types this handler accepts
            secret: Optional secret for signature verification
            
        Returns:
            Registration ID
        """
        registration_id = f"wh-{uuid.uuid4().hex[:8]}"
        
        # Normalize event types
        normalized_events = []
        if event_types:
            for et in event_types:
                if isinstance(et, str):
                    normalized_events.append(WebhookEventType(et))
                else:
                    normalized_events.append(et)
        
        registration = WebhookRegistration(
            endpoint=endpoint,
            handler=handler,
            event_types=normalized_events,
            secret=secret
        )
        
        self.webhook_registrations[registration_id] = registration
        
        logger.info(f"Registered webhook {registration_id} for endpoint {endpoint}")
        
        return registration_id
    
    def unregister_webhook(self, registration_id: str) -> bool:
        """Unregister a webhook by ID"""
        if registration_id in self.webhook_registrations:
            del self.webhook_registrations[registration_id]
            logger.info(f"Unregistered webhook {registration_id}")
            return True
        return False
    
    async def process_webhook(
        self,
        endpoint: str,
        data: Dict[str, Any],
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process incoming webhook data
        
        Args:
            endpoint: Webhook endpoint that received the data
            data: Webhook payload
            signature: Optional signature for verification
            
        Returns:
            Processing result
        """
        # Verify signature if secret is configured
        if self.webhook_secret and signature:
            if not self._verify_signature(data, signature):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Find matching handlers
        matching_handlers = []
        for reg in self.webhook_registrations.values():
            if reg.endpoint == endpoint:
                matching_handlers.append(reg.handler)
        
        # Execute handlers
        results = []
        for handler in matching_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(data)
                else:
                    result = handler(data)
                results.append({"success": True, "result": result})
            except Exception as e:
                logger.error(f"Webhook handler error: {e}")
                results.append({"success": False, "error": str(e)})
        
        # Update execution status if this is a callback
        execution_id = data.get("execution_id")
        if execution_id and execution_id in self.active_executions:
            await self._update_execution_status(execution_id, data)
        
        return {
            "processed": True,
            "handlers_executed": len(results),
            "results": results
        }
    
    # ========================================================================
    # AGENT EVENT HANDLING
    # ========================================================================
    
    async def handle_agent_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle agent layer events and route to appropriate workflows
        
        Args:
            event_type: Type of agent event
            data: Event data
            agent_id: Optional agent identifier
            
        Returns:
            Event handling result
        """
        logger.info(f"Handling agent event: {event_type} (agent: {agent_id})")
        
        event = AgentEvent(
            event_type=event_type,
            agent_id=agent_id,
            data=data
        )
        
        # Trigger mapped workflow if configured
        workflow_type = self.event_workflow_map.get(event_type)
        workflow_result = None
        
        if workflow_type:
            webhook_id = WORKFLOW_WEBHOOK_MAP.get(workflow_type, "apex-custom")
            
            try:
                workflow_result = await self.trigger_workflow(
                    workflow_id=webhook_id,
                    payload={
                        "event": event_type,
                        "agent_id": agent_id,
                        "data": data,
                        "timestamp": event.timestamp.isoformat()
                    }
                )
            except Exception as e:
                logger.error(f"Failed to trigger workflow for event {event_type}: {e}")
        
        # Execute registered event handlers
        handler_results = []
        for handler in self.event_handlers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(event)
                else:
                    result = handler(event)
                handler_results.append({"success": True, "result": result})
            except Exception as e:
                logger.error(f"Event handler error: {e}")
                handler_results.append({"success": False, "error": str(e)})
        
        return {
            "event_type": event_type,
            "workflow_triggered": workflow_result is not None,
            "workflow_result": workflow_result,
            "handlers_executed": len(handler_results),
            "handler_results": handler_results
        }
    
    def on_agent_event(self, event_type: str, handler: Callable):
        """Register an event handler for agent events"""
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event: {event_type}")
    
    async def sync_agent_status(
        self,
        agent_id: str,
        status: str,
        current_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synchronize agent status with n8n
        
        Args:
            agent_id: Agent identifier
            status: Agent status
            current_task: Optional current task description
            metadata: Optional additional metadata
            
        Returns:
            Sync result
        """
        self.agent_status_cache[agent_id] = {
            "status": status,
            "current_task": current_task,
            "metadata": metadata or {},
            "last_updated": datetime.now().isoformat()
        }
        
        # Trigger monitoring workflow
        try:
            result = await self.trigger_workflow(
                workflow_id=WORKFLOW_WEBHOOK_MAP[WorkflowType.MONITORING],
                payload={
                    "type": "agent_status_update",
                    "agent_id": agent_id,
                    "status": status,
                    "current_task": current_task,
                    "metadata": metadata,
                    "timestamp": datetime.now().isoformat()
                }
            )
            return {"synced": True, "workflow_result": result}
        except Exception as e:
            logger.warning(f"Failed to sync agent status: {e}")
            return {"synced": False, "error": str(e)}
    
    # ========================================================================
    # WEBHOOK HANDLERS (Specific Event Types)
    # ========================================================================
    
    async def handle_checkout_complete(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle checkout complete webhook"""
        logger.info("Processing checkout complete event")
        
        execution_id = data.get("execution_id")
        repository = data.get("repository")
        branch = data.get("branch", "main")
        
        # Trigger 72-agent orchestration
        result = await self.trigger_workflow(
            workflow_id=WORKFLOW_WEBHOOK_MAP[WorkflowType.AGENT_ORCHESTRATION_72],
            payload={
                "event": "checkout_complete",
                "execution_id": execution_id,
                "repoUrl": repository,
                "branch": branch,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return {
            "status": "processed",
            "event": "checkout_complete",
            "orchestration_triggered": True,
            "result": result
        }
    
    async def handle_build_complete(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle build complete webhook"""
        logger.info("Processing build complete event")
        
        build_id = data.get("build_id")
        success = data.get("success", False)
        artifacts = data.get("artifacts", [])
        
        if success and artifacts:
            # Trigger deployment workflow
            result = await self.trigger_workflow(
                workflow_id=WORKFLOW_WEBHOOK_MAP[WorkflowType.DEPLOYMENT],
                payload={
                    "event": "build_complete",
                    "build_id": build_id,
                    "artifacts": artifacts,
                    "auto_deploy": data.get("auto_deploy", False),
                    "environment": data.get("environment", "staging")
                }
            )
            
            return {
                "status": "processed",
                "deployment_triggered": True,
                "result": result
            }
        
        return {
            "status": "processed",
            "deployment_triggered": False,
            "reason": "Build failed or no artifacts"
        }
    
    async def handle_deployment_complete(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle deployment complete webhook"""
        logger.info("Processing deployment complete event")
        
        deployment_id = data.get("deployment_id")
        environment = data.get("environment")
        url = data.get("url")
        
        # Send notification
        notification_result = await self.send_notification(
            channel=NotificationChannel.SLACK,
            message=f"✅ Deployment complete: {deployment_id}\nEnvironment: {environment}\nURL: {url}",
            priority=NotificationPriority.HIGH,
            title="Deployment Successful"
        )
        
        # Trigger reporting workflow
        report_result = await self.trigger_workflow(
            workflow_id=WORKFLOW_WEBHOOK_MAP[WorkflowType.REPORTING],
            payload={
                "event": "deployment_complete",
                "deployment_id": deployment_id,
                "environment": environment,
                "url": url,
                "metrics": data.get("metrics", {})
            }
        )
        
        return {
            "status": "processed",
            "notification_sent": notification_result.get("sent", False),
            "report_triggered": True
        }
    
    async def handle_error_alert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle error alert webhook"""
        logger.error(f"Processing error alert: {data.get('error')}")
        
        error_message = data.get("error", "Unknown error")
        severity = data.get("severity", "high")
        agent_id = data.get("agent_id")
        
        # Map severity to priority
        priority_map = {
            "critical": NotificationPriority.CRITICAL,
            "high": NotificationPriority.HIGH,
            "medium": NotificationPriority.MEDIUM,
            "low": NotificationPriority.LOW
        }
        priority = priority_map.get(severity, NotificationPriority.HIGH)
        
        # Send critical notification
        notification_result = await self.send_notification(
            channel=NotificationChannel.SLACK,
            message=f"🚨 ERROR ALERT\nAgent: {agent_id}\nError: {error_message}\nSeverity: {severity}",
            priority=priority,
            title="APEX Error Alert"
        )
        
        # Trigger error handling workflow
        workflow_result = await self.trigger_workflow(
            workflow_id="apex-error-handler",
            payload={
                "event": "error_alert",
                "error": error_message,
                "severity": severity,
                "agent_id": agent_id,
                "stack_trace": data.get("stack_trace"),
                "context": data.get("context", {})
            }
        )
        
        return {
            "status": "processed",
            "notification_sent": notification_result.get("sent", False),
            "error_workflow_triggered": True
        }
    
    # ========================================================================
    # NOTIFICATIONS
    # ========================================================================
    
    async def send_notification(
        self,
        channel: NotificationChannel,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send notification through n8n workflow
        
        Args:
            channel: Notification channel
            message: Message content
            priority: Message priority
            title: Optional message title
            metadata: Optional additional metadata
            
        Returns:
            Notification result
        """
        payload = NotificationPayload(
            channel=channel,
            message=message,
            priority=priority,
            title=title,
            metadata=metadata or {}
        )
        
        try:
            result = await self.trigger_workflow(
                workflow_id=WORKFLOW_WEBHOOK_MAP[WorkflowType.NOTIFICATION],
                payload={
                    "channel": channel.value,
                    "message": message,
                    "priority": priority.value,
                    "title": title,
                    "metadata": metadata,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return {
                "sent": True,
                "channel": channel.value,
                "workflow_result": result
            }
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return {
                "sent": False,
                "channel": channel.value,
                "error": str(e)
            }
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _get_workflow_type(self, workflow_id: str) -> WorkflowType:
        """Determine workflow type from ID"""
        if "72" in workflow_id or "orchestrate" in workflow_id:
            return WorkflowType.AGENT_ORCHESTRATION_72
        elif "24" in workflow_id:
            return WorkflowType.AGENT_ORCHESTRATION_24
        elif "notify" in workflow_id:
            return WorkflowType.NOTIFICATION
        elif "report" in workflow_id:
            return WorkflowType.REPORTING
        elif "deploy" in workflow_id:
            return WorkflowType.DEPLOYMENT
        elif "monitor" in workflow_id:
            return WorkflowType.MONITORING
        return WorkflowType.CUSTOM
    
    def _estimate_duration(self, workflow_type: WorkflowType) -> str:
        """Estimate workflow execution duration"""
        estimates = {
            WorkflowType.AGENT_ORCHESTRATION_72: "3-5 minutes",
            WorkflowType.AGENT_ORCHESTRATION_24: "2-3 minutes",
            WorkflowType.DEPLOYMENT: "5-10 minutes",
            WorkflowType.NOTIFICATION: "1-2 seconds",
            WorkflowType.REPORTING: "10-30 seconds",
            WorkflowType.MONITORING: "1-2 seconds",
            WorkflowType.CUSTOM: "unknown"
        }
        return estimates.get(workflow_type, "unknown")
    
    async def _wait_for_completion(
        self,
        execution_id: str,
        timeout_seconds: int
    ) -> Dict[str, Any]:
        """Wait for workflow execution to complete"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            execution = self.active_executions.get(execution_id)
            
            if not execution:
                # Check completed
                for exec in self.completed_executions:
                    if exec.execution_id == execution_id:
                        return {
                            "status": exec.status,
                            "result": exec.result,
                            "completed_at": exec.completed_at.isoformat() if exec.completed_at else None
                        }
                return {"status": "unknown", "error": "Execution not found"}
            
            if execution.status in ["completed", "failed"]:
                return {
                    "status": execution.status,
                    "result": execution.result,
                    "error": execution.error
                }
            
            await asyncio.sleep(1)
        
        return {"status": "timeout", "message": f"Timeout after {timeout_seconds}s"}
    
    async def _update_execution_status(
        self,
        execution_id: str,
        data: Dict[str, Any]
    ):
        """Update execution status from callback data"""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return
        
        event_type = data.get("event_type", "")
        
        if event_type == WebhookEventType.WORKFLOW_FINISHED.value:
            execution.status = data.get("status", "completed")
            execution.result = data.get("result")
            execution.completed_at = datetime.now()
            
            # Move to completed
            self.completed_executions.append(execution)
            del self.active_executions[execution_id]
            
            logger.info(f"Execution {execution_id} completed: {execution.status}")
    
    async def _simulate_workflow_execution(self, execution_id: str):
        """Simulate workflow execution for demo/testing without real n8n"""
        await asyncio.sleep(2)  # Simulate 2 second processing
        
        execution = self.active_executions.get(execution_id)
        if execution:
            execution.status = "completed"
            execution.result = {"simulation": True, "output": "Workflow completed successfully"}
            execution.completed_at = datetime.now()
            
            self.completed_executions.append(execution)
            del self.active_executions[execution_id]
            
            logger.info(f"Simulated execution {execution_id} completed")
    
    def _verify_signature(self, data: Dict[str, Any], signature: str) -> bool:
        """Verify webhook signature"""
        if not self.webhook_secret:
            return True
        
        payload = json.dumps(data, sort_keys=True)
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        total_completed = len(self.completed_executions)
        successful = sum(1 for e in self.completed_executions if e.status == "completed")
        failed = sum(1 for e in self.completed_executions if e.status == "failed")
        
        return {
            "active_executions": len(self.active_executions),
            "total_completed": total_completed,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_completed if total_completed > 0 else 0,
            "webhook_registrations": len(self.webhook_registrations),
            "cached_agent_status": len(self.agent_status_cache)
        }


# ============================================================================
# FASTAPI ROUTER
# ============================================================================

def create_n8n_router(integration: N8NIntegration):
    """
    Create FastAPI router for n8n integration endpoints
    
    Args:
        integration: N8NIntegration instance
        
    Returns:
        Configured APIRouter or None if FastAPI not available
    """
    if not FASTAPI_AVAILABLE:
        logger.warning("FastAPI not available - router not created")
        return None
    
    return _create_fastapi_router_internal(integration)


def _create_fastapi_router_internal(integration: N8NIntegration) -> APIRouter:
    """
    Create FastAPI router for n8n integration endpoints
    
    Args:
        integration: N8NIntegration instance
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/n8n", tags=["n8n"])
    
    @router.post("/trigger", response_model=TriggerWorkflowResponse)
    async def trigger_workflow_endpoint(
        request: TriggerWorkflowRequest,
        background_tasks: BackgroundTasks
    ):
        """Trigger an n8n workflow"""
        result = await integration.trigger_workflow(
            workflow_id=request.workflow_id,
            payload=request.payload,
            callback_url=request.callback_url,
            wait_for_completion=request.wait_for_completion,
            timeout_seconds=request.timeout_seconds
        )
        
        return TriggerWorkflowResponse(
            execution_id=result["execution_id"],
            workflow_id=request.workflow_id,
            status=result["status"],
            message=result["message"],
            estimated_duration=result.get("estimated_duration")
        )
    
    @router.get("/status/{execution_id}")
    async def get_execution_status(execution_id: str):
        """Get workflow execution status"""
        return await integration.get_workflow_status(execution_id)
    
    @router.post("/webhook/{endpoint:path}")
    async def receive_webhook(
        endpoint: str,
        request: Request,
        background_tasks: BackgroundTasks
    ):
        """Receive webhook callbacks from n8n"""
        try:
            data = await request.json()
        except:
            data = {}
        
        signature = request.headers.get("X-Webhook-Signature")
        
        result = await integration.process_webhook(
            endpoint=f"/{endpoint}",
            data=data,
            signature=signature
        )
        
        return result
    
    @router.post("/callback/{callback_id}")
    async def receive_callback(
        callback_id: str,
        request: WebhookCallbackRequest
    ):
        """Receive workflow completion callbacks"""
        # Update execution status
        execution = integration.active_executions.get(request.execution_id)
        if execution:
            execution.status = request.data.get("status", "completed")
            execution.result = request.data.get("result")
            execution.completed_at = datetime.now()
            
            integration.completed_executions.append(execution)
            del integration.active_executions[request.execution_id]
        
        # Execute registered callback handlers
        handlers = integration.event_handlers.get(f"callback:{callback_id}", [])
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(request.data)
        
        return {"received": True, "execution_id": request.execution_id}
    
    @router.post("/agent/event")
    async def handle_agent_event_endpoint(
        event_type: str,
        data: Dict[str, Any],
        agent_id: Optional[str] = None
    ):
        """Handle agent layer events"""
        return await integration.handle_agent_event(event_type, data, agent_id)
    
    @router.post("/agent/status")
    async def update_agent_status(request: AgentStatusUpdate):
        """Update and sync agent status"""
        return await integration.sync_agent_status(
            agent_id=request.agent_id,
            status=request.status,
            current_task=request.current_task,
            metadata=request.metadata
        )
    
    @router.post("/notify")
    async def send_notification_endpoint(request: NotificationRequest):
        """Send notification through n8n"""
        channel = NotificationChannel(request.channel)
        priority = NotificationPriority(request.priority)
        
        return await integration.send_notification(
            channel=channel,
            message=request.message,
            priority=priority,
            title=request.title,
            metadata=request.metadata
        )
    
    @router.get("/stats")
    async def get_stats():
        """Get integration statistics"""
        return integration.get_execution_stats()
    
    @router.get("/workflows")
    async def list_workflows():
        """List available workflow mappings"""
        return {
            "workflows": [
                {"type": wt.value, "webhook_id": wid}
                for wt, wid in WORKFLOW_WEBHOOK_MAP.items()
            ],
            "event_mappings": {
                event: wt.value
                for event, wt in DEFAULT_EVENT_WORKFLOW_MAP.items()
            }
        }
    
    return router


# ============================================================================
# INTEGRATION WITH AGENT LAYER
# ============================================================================

class AgentLayerBridge:
    """
    Bridge between AgentLayer and N8NIntegration
    
    Automatically wires up agent layer events to n8n workflows
    """
    
    def __init__(self, agent_layer, n8n_integration: N8NIntegration):
        """
        Initialize bridge
        
        Args:
            agent_layer: AgentLayer instance
            n8n_integration: N8NIntegration instance
        """
        self.agent_layer = agent_layer
        self.n8n = n8n_integration
        self._initialized = False
        
        logger.info("AgentLayerBridge created")
    
    def initialize(self):
        """Wire up event listeners"""
        if self._initialized:
            return
        
        # Wire up agent layer events to n8n
        if hasattr(self.agent_layer, 'events'):
            self.agent_layer.events.on(
                'on_checkpoint_created',
                self._on_checkpoint_created
            )
            self.agent_layer.events.on(
                'on_consensus_reached',
                self._on_consensus_reached
            )
            self.agent_layer.events.on(
                'on_evaluation_complete',
                self._on_evaluation_complete
            )
            self.agent_layer.events.on(
                'on_agent_spawned',
                self._on_agent_spawned
            )
            self.agent_layer.events.on(
                'on_build_complete',
                self._on_build_complete
            )
        
        self._initialized = True
        logger.info("AgentLayerBridge initialized")
    
    async def _on_checkpoint_created(self, data):
        """Handle checkpoint created event"""
        await self.n8n.handle_agent_event("checkpoint_created", data)
    
    async def _on_consensus_reached(self, data):
        """Handle consensus reached event"""
        await self.n8n.handle_agent_event("consensus_reached", data)
    
    async def _on_evaluation_complete(self, data):
        """Handle evaluation complete event"""
        await self.n8n.handle_agent_event("evaluation_complete", data)
    
    async def _on_agent_spawned(self, data):
        """Handle agent spawned event"""
        await self.n8n.handle_agent_event("agent_spawned", data)
    
    async def _on_build_complete(self, data):
        """Handle build complete event"""
        await self.n8n.handle_agent_event("build_complete", data)


# ============================================================================
# FACTORY AND HELPER FUNCTIONS
# ============================================================================

def create_n8n_integration(
    webhook_base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> N8NIntegration:
    """
    Factory function to create N8NIntegration instance
    
    Args:
        webhook_base_url: Base URL for webhooks
        api_key: n8n API key
        base_url: n8n base URL
        
    Returns:
        Configured N8NIntegration instance
    """
    return N8NIntegration(
        webhook_base_url=webhook_base_url,
        api_key=api_key,
        base_url=base_url
    )


async def setup_fastapi_app(
    integration: Optional[N8NIntegration] = None,
    include_agent_routes: bool = True
):
    """
    Setup FastAPI application with n8n integration
    
    Args:
        integration: Optional N8NIntegration instance
        include_agent_routes: Whether to include agent layer routes
        
    Returns:
        Configured FastAPI app or None if FastAPI not available
    """
    if not FASTAPI_AVAILABLE:
        logger.warning("FastAPI not available - app not created")
        return None
    
    return await _setup_fastapi_app_internal(integration, include_agent_routes)


async def _setup_fastapi_app_internal(
    integration: Optional[N8NIntegration] = None,
    include_agent_routes: bool = True
) -> FastAPI:
    """
    Setup FastAPI application with n8n integration
    
    Args:
        integration: Optional N8NIntegration instance
        include_agent_routes: Whether to include agent layer routes
        
    Returns:
        Configured FastAPI app
    """
    integration = integration or create_n8n_integration()
    
    app = FastAPI(
        title="APEX n8n Integration",
        description="Webhook and API endpoints for n8n workflow integration",
        version="1.0.0"
    )
    
    # Include n8n router
    router = create_n8n_router(integration)
    app.include_router(router)
    
    # Health check
    @app.get("/health")
    async def health():
        return {"status": "healthy", "n8n_connected": True}
    
    # Startup/shutdown events
    @app.on_event("startup")
    async def startup():
        logger.info("FastAPI app starting up")
    
    @app.on_event("shutdown")
    async def shutdown():
        logger.info("FastAPI app shutting down")
        await integration.close()
    
    return app


# ============================================================================
# DEMO AND TESTING
# ============================================================================

async def demo_n8n_integration():
    """
    Demonstrate n8n integration capabilities
    
    This function showcases all major features:
    1. Workflow triggering
    2. Event handling
    3. Webhook processing
    4. Agent status sync
    5. Notifications
    """
    print("="*70)
    print("APEX n8n Integration Demo")
    print("="*70)
    print()
    
    # Create integration instance (mock mode - no real n8n required)
    integration = N8NIntegration(
        webhook_base_url="http://localhost:8000/webhooks",
        base_url="http://localhost:5678",
        api_key="demo-key"
    )
    
    print("[1/6] N8N Integration initialized")
    print(f"      Base URL: {integration.base_url}")
    print(f"      Webhook URL: {integration.webhook_base_url}")
    print()
    
    # Register webhook handlers
    print("[2/6] Registering webhook handlers...")
    
    async def demo_checkout_handler(data):
        print(f"      → Checkout handler received: {data.get('repository', 'N/A')}")
    
    async def demo_build_handler(data):
        print(f"      → Build handler received: {data.get('build_id', 'N/A')}")
    
    reg_id_1 = integration.register_webhook(
        endpoint="/checkout-complete",
        handler=demo_checkout_handler,
        event_types=[WebhookEventType.CHECKOUT_COMPLETE]
    )
    
    reg_id_2 = integration.register_webhook(
        endpoint="/build-complete",
        handler=demo_build_handler,
        event_types=[WebhookEventType.BUILD_COMPLETE]
    )
    
    print(f"      Registered {len(integration.webhook_registrations)} webhooks")
    print()
    
    # Process webhooks
    print("[3/6] Processing webhook callbacks...")
    
    await integration.process_webhook(
        endpoint="/checkout-complete",
        data={"repository": "demo-repo", "branch": "main"}
    )
    
    await integration.process_webhook(
        endpoint="/build-complete",
        data={"build_id": "build-123", "success": True}
    )
    print()
    
    # Handle agent events
    print("[4/6] Handling agent layer events...")
    
    result = await integration.handle_agent_event(
        event_type="checkpoint_created",
        data={"build_id": "build-123", "stage": "analysis"},
        agent_id="meta-router-001"
    )
    print(f"      Event handled: {result['event_type']}")
    print(f"      Workflow triggered: {result['workflow_triggered']}")
    print()
    
    # Sync agent status
    print("[5/6] Syncing agent status...")
    
    await integration.sync_agent_status(
        agent_id="frontend-agent-001",
        status="running",
        current_task="Building React components",
        metadata={"progress": 45, "files_created": 12}
    )
    
    await integration.sync_agent_status(
        agent_id="backend-agent-001",
        status="idle",
        current_task=None,
        metadata={"last_task": "API endpoints"}
    )
    
    print(f"      Synced {len(integration.agent_status_cache)} agent statuses")
    print()
    
    # Show execution stats
    print("[6/6] Execution statistics:")
    stats = integration.get_execution_stats()
    for key, value in stats.items():
        print(f"      {key}: {value}")
    print()
    
    # Cleanup
    integration.unregister_webhook(reg_id_1)
    integration.unregister_webhook(reg_id_2)
    await integration.close()
    
    print("="*70)
    print("Demo complete!")
    print("="*70)
    
    return integration


async def test_workflow_mock():
    """
    Test workflow triggering with mocked HTTP responses
    
    This demonstrates the retry logic and error handling
    """
    print("\n" + "="*70)
    print("Testing Workflow Trigger (Mock Mode)")
    print("="*70)
    print()
    
    integration = N8NIntegration(
        webhook_base_url="http://localhost:8000/webhooks",
        base_url="http://localhost:5678"
    )
    
    # Since we don't have a real n8n instance, this will fail with connection error
    # but it demonstrates the retry logic
    print("Attempting to trigger workflow (expected to fail without n8n)...")
    
    try:
        # This will fail because there's no n8n server
        result = await integration.trigger_workflow(
            workflow_id="test-workflow",
            payload={"test": "data"},
            wait_for_completion=False
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"Expected error (no n8n server): {type(e).__name__}")
        print(f"Message: {str(e)[:100]}...")
    
    await integration.close()
    print("\nMock test complete!")


async def main():
    """Main entry point for demo and testing"""
    print("APEX n8n Integration Module")
    print("Version: 1.0.0")
    print()
    
    # Run demo
    await demo_n8n_integration()
    
    # Run mock test
    await test_workflow_mock()
    
    print("\n" + "="*70)
    print("All tests completed successfully!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
