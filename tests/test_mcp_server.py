#!/usr/bin/env python3
"""
Test Suite: MCP Server

Comprehensive tests for MCP server endpoints and functionality.

Coverage:
- Server initialization
- Tool listing
- Tool execution
- Build context management
- Error handling
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Need to add parent to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server import MasterBuilder7MCPServer, BuildContext
from mcp.types import TextContent


# =============================================================================
# BuildContext Tests
# =============================================================================

class TestBuildContext:
    """Test BuildContext dataclass."""
    
    def test_context_creation(self):
        """Test build context creation."""
        context = BuildContext(
            project_path="/path/to/project",
            build_id="build-123",
            agents_active=["agent-1"],
            checkpoints=["checkpoint-1"]
        )
        
        assert context.project_path == "/path/to/project"
        assert context.build_id == "build-123"
        assert context.agents_active == ["agent-1"]
        assert context.checkpoints == ["checkpoint-1"]
        assert context.status == "idle"
    
    def test_context_creation_custom_status(self):
        """Test build context with custom status."""
        context = BuildContext(
            project_path="/path/to/project",
            build_id="build-123",
            agents_active=[],
            checkpoints=[],
            status="building",
            current_agent="agent-1"
        )
        
        assert context.status == "building"
        assert context.current_agent == "agent-1"


# =============================================================================
# MasterBuilder7MCPServer Tests
# =============================================================================

@pytest.mark.asyncio
class TestMasterBuilder7MCPServer:
    """Test MasterBuilder7MCPServer."""
    
    def test_server_initialization(self):
        """Test server initialization."""
        server = MasterBuilder7MCPServer()
        
        assert server.server is not None
        assert server.context is None
        assert server.yolo_mode is False
    
    async def test_analyze_project(self):
        """Test analyze_project tool."""
        server = MasterBuilder7MCPServer()
        
        # Mock the meta-router to avoid actual analysis
        with patch('mcp_server.MetaRouterAgent') as mock_router:
            mock_instance = MagicMock()
            mock_instance.analyze_repository = AsyncMock(return_value={
                "stack": "python",
                "framework": "fastapi"
            })
            mock_router.return_value = mock_instance
            
            result = await server._analyze_project({
                "project_path": "/test/path",
                "project_name": "test_project"
            })
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "stack" in result[0].text
    
    async def test_analyze_project_error(self):
        """Test analyze_project with error."""
        server = MasterBuilder7MCPServer()
        
        with patch('mcp_server.MetaRouterAgent') as mock_router:
            mock_router.side_effect = Exception("Analysis failed")
            
            result = await server._analyze_project({
                "project_path": "/test/path"
            })
        
        assert len(result) == 1
        assert "Analysis error" in result[0].text
    
    async def test_execute_build_yolo_mode(self):
        """Test execute_build in YOLO mode."""
        server = MasterBuilder7MCPServer()
        
        result = await server._execute_build({
            "project_path": "/test/path",
            "yolo_mode": True,
            "max_agents": 64
        })
        
        assert len(result) == 1
        assert "YOLO MODE" in result[0].text
        assert server.yolo_mode is True
        assert server.context is not None
        assert server.context.project_path == "/test/path"
    
    async def test_execute_build_controlled_mode(self):
        """Test execute_build in controlled mode."""
        server = MasterBuilder7MCPServer()
        
        result = await server._execute_build({
            "project_path": "/test/path",
            "yolo_mode": False
        })
        
        assert len(result) == 1
        assert "controlled" in result[0].text.lower()
    
    async def test_spawn_agent(self):
        """Test spawn_agent tool."""
        server = MasterBuilder7MCPServer()
        
        # Set up context first
        server.context = BuildContext(
            project_path="/test",
            build_id="build-123",
            agents_active=[],
            checkpoints=[]
        )
        
        result = await server._spawn_agent({
            "agent_type": "code_generator",
            "task": "Generate API endpoints",
            "context": {"framework": "fastapi"}
        })
        
        assert len(result) == 1
        assert "code_generator" in result[0].text
        assert "Generate API endpoints" in result[0].text
        assert "code_generator" in server.context.agents_active
    
    async def test_create_checkpoint(self):
        """Test create_checkpoint tool."""
        server = MasterBuilder7MCPServer()
        
        server.context = BuildContext(
            project_path="/test",
            build_id="build-123",
            agents_active=[],
            checkpoints=[]
        )
        
        result = await server._create_checkpoint({
            "build_id": "build-123",
            "stage": "validation",
            "data": {"status": "passed"}
        })
        
        assert len(result) == 1
        assert "Checkpoint Created" in result[0].text
        assert "validation" in result[0].text
        assert len(server.context.checkpoints) == 1
    
    async def test_run_security_audit(self):
        """Test run_security_audit tool."""
        server = MasterBuilder7MCPServer()
        
        result = await server._run_security_audit({
            "project_path": "/test/path",
            "auto_fix": True
        })
        
        assert len(result) == 1
        assert "Security Audit Complete" in result[0].text
        assert "Score:" in result[0].text
    
    async def test_optimize_performance(self):
        """Test optimize_performance tool."""
        server = MasterBuilder7MCPServer()
        
        result = await server._optimize_performance({
            "route_code": "def handler(): pass",
            "use_quantum": True
        })
        
        assert len(result) == 1
        assert "Performance Optimization" in result[0].text
        assert "Quantum mode: Enabled" in result[0].text
    
    async def test_verify_rewards(self):
        """Test verify_rewards tool."""
        server = MasterBuilder7MCPServer()
        
        result = await server._verify_rewards({
            "reward_data": {"amount": 100, "user": "test"},
            "check_fraud": True
        })
        
        assert len(result) == 1
        assert "Reward Verification" in result[0].text
        assert "VALID" in result[0].text
    
    async def test_get_build_status_no_context(self):
        """Test get_build_status with no active build."""
        server = MasterBuilder7MCPServer()
        
        result = await server._get_build_status()
        
        assert len(result) == 1
        assert "No active build" in result[0].text
    
    async def test_get_build_status_with_context(self):
        """Test get_build_status with active build."""
        server = MasterBuilder7MCPServer()
        
        server.context = BuildContext(
            project_path="/test/path",
            build_id="build-123",
            agents_active=["agent-1", "agent-2"],
            checkpoints=["cp-1", "cp-2"],
            status="building"
        )
        server.yolo_mode = True
        
        result = await server._get_build_status()
        
        assert len(result) == 1
        assert "build-123" in result[0].text
        assert "2" in result[0].text  # Active agents count
        assert "YOLO Mode: ON" in result[0].text
    
    async def test_yolo_mode_enable(self):
        """Test yolo_mode_enable tool."""
        server = MasterBuilder7MCPServer()
        
        result = await server._yolo_mode_enable({
            "project_path": "/test/path",
            "safety_threshold": 0.8
        })
        
        assert len(result) == 1
        assert "YOLO MODE ENGAGED" in result[0].text
        assert server.yolo_mode is True
        assert server.context is not None
        assert "0.8" in result[0].text
    
    async def test_rollback(self):
        """Test rollback tool."""
        server = MasterBuilder7MCPServer()
        
        result = await server._rollback({
            "checkpoint_id": "checkpoint-123"
        })
        
        assert len(result) == 1
        assert "Rollback Initiated" in result[0].text
        assert "checkpoint-123" in result[0].text


# =============================================================================
# Tool Schema Tests
# =============================================================================

class TestToolSchemas:
    """Test MCP tool schemas."""
    
    def test_analyze_project_schema(self):
        """Test analyze_project schema."""
        server = MasterBuilder7MCPServer()
        
        # Get tool list
        tools = asyncio.run(server.server._request_handlers['tools/list']())
        
        analyze_tool = next(t for t in tools if t.name == "analyze_project")
        
        assert analyze_tool is not None
        assert "project_path" in analyze_tool.inputSchema["properties"]
        assert "project_path" in analyze_tool.inputSchema["required"]
    
    def test_execute_build_schema(self):
        """Test execute_build schema."""
        server = MasterBuilder7MCPServer()
        
        tools = asyncio.run(server.server._request_handlers['tools/list']())
        
        build_tool = next(t for t in tools if t.name == "execute_build")
        
        assert build_tool is not None
        assert "yolo_mode" in build_tool.inputSchema["properties"]
        assert "max_agents" in build_tool.inputSchema["properties"]
        # yolo_mode has default, so not required
        assert "project_path" in build_tool.inputSchema["required"]


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
class TestMCPErrorHandling:
    """Test MCP server error handling."""
    
    async def test_unknown_tool(self):
        """Test handling of unknown tool."""
        server = MasterBuilder7MCPServer()
        
        # This should not raise but return error content
        result = await server.call_tool("unknown_tool", {})
        
        assert len(result) == 1
        assert "Error" in result[0].text
    
    async def test_security_audit_import_error(self):
        """Test security audit with import error."""
        server = MasterBuilder7MCPServer()
        
        with patch.dict('sys.modules', {'paystack_security_agent': None}):
            result = await server._run_security_audit({
                "project_path": "/test",
                "auto_fix": False
            })
        
        # Should handle gracefully
        assert len(result) == 1
