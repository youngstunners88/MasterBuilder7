#!/usr/bin/env python3
"""MCP HTTP Server with /deploy endpoint and approval gate"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import sys
sys.path.insert(0, '/home/workspace/MasterBuilder7')
from REAL_BUILDER import RealBuilder

APPROVAL_QUEUE = {}
DEPLOYMENTS = []
API_KEY = os.getenv('MCP_API_KEY', 'dev-key-change-in-production')

class MCPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self._respond(200, {"status": "healthy"})
        elif self.path == '/status':
            self._respond(200, {
                "pending_approvals": len(APPROVAL_QUEUE),
                "total_deployments": len(DEPLOYMENTS)
            })
        else:
            self._respond(404, {"error": "Not found"})
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        
        try:
            data = json.loads(body)
        except:
            self._respond(400, {"error": "Invalid JSON"})
            return
        
        # Verify API key
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer ') or auth[7:] != API_KEY:
            self._respond(401, {"error": "Invalid API key"})
            return
        
        if self.path == '/deploy':
            self._handle_deploy(data)
        elif self.path.startswith('/approve/'):
            deployment_id = self.path.split('/')[-1]
            self._handle_approve(deployment_id, data)
        else:
            self._respond(404, {"error": "Not found"})
    
    def _handle_deploy(self, data):
        repo = data.get('repo', '/home/workspace/iHhashi')
        track = data.get('track', 'internal')
        require_approval = data.get('require_approval', track == 'production')
        
        deployment_id = f"dep-{os.urandom(4).hex()}"
        
        if require_approval and track == 'production':
            APPROVAL_QUEUE[deployment_id] = {
                'repo': repo,
                'track': track,
                'status': 'pending_approval'
            }
            self._respond(202, {
                "deployment_id": deployment_id,
                "status": "pending_approval",
                "message": "Production deployment requires approval. POST to /approve/{id}"
            })
            return
        
        # Execute deployment
        builder = RealBuilder(repo)
        result = builder.build_and_deploy(track)
        
        DEPLOYMENTS.append({
            'id': deployment_id,
            'result': result
        })
        
        self._respond(200, {
            "deployment_id": deployment_id,
            "status": "completed" if result['success'] else "failed",
            "result": result
        })
    
    def _handle_approve(self, deployment_id, data):
        if deployment_id not in APPROVAL_QUEUE:
            self._respond(404, {"error": "Deployment not found"})
            return
        
        approved = data.get('approved', False)
        if not approved:
            del APPROVAL_QUEUE[deployment_id]
            self._respond(200, {"status": "rejected"})
            return
        
        # Execute approved deployment
        item = APPROVAL_QUEUE.pop(deployment_id)
        builder = RealBuilder(item['repo'])
        result = builder.build_and_deploy(item['track'])
        
        DEPLOYMENTS.append({
            'id': deployment_id,
            'result': result
        })
        
        self._respond(200, {
            "deployment_id": deployment_id,
            "status": "completed" if result['success'] else "failed",
            "result": result
        })
    
    def _respond(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

if __name__ == '__main__':
    port = int(os.getenv('MCP_PORT', 8765))
    server = HTTPServer(('0.0.0.0', port), MCPHandler)
    print(f"🚀 MCP Server running on http://0.0.0.0:{port}")
    print(f"   Health: http://0.0.0.0:{port}/health")
    print(f"   Deploy: POST http://0.0.0.0:{port}/deploy")
    server.serve_forever()
