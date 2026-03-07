#!/usr/bin/env bun
/**
 * MasterBuilder7 Dashboard
 * Real-time monitoring + cost tracking
 */

import { serve } from 'bun';
import { Client } from 'pg';
import Redis from 'ioredis';

const HTML = `<!DOCTYPE html>
<html>
<head>
  <title>MB7 Dashboard</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      font-family: -apple-system, system-ui, sans-serif; 
      background: #0a0a0a;
      color: #fff;
      padding: 20px;
    }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
    .card {
      background: #1a1a1a;
      border-radius: 12px;
      padding: 20px;
      border: 1px solid #333;
    }
    .card h3 { color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 10px; }
    .metric { font-size: 32px; font-weight: bold; }
    .metric.ok { color: #22c55e; }
    .metric.warn { color: #eab308; }
    .metric.critical { color: #ef4444; }
    .metric.killed { color: #dc2626; text-decoration: line-through; }
    .bar { height: 8px; background: #333; border-radius: 4px; margin-top: 10px; overflow: hidden; }
    .bar-fill { height: 100%; transition: width 0.3s; }
    .bar-fill.ok { background: #22c55e; }
    .bar-fill.warn { background: #eab308; }
    .bar-fill.critical { background: #ef4444; }
    .agents { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 15px; }
    .agent {
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
    }
    .agent.idle { background: #1e3a5f; color: #60a5fa; }
    .agent.active { background: #14532d; color: #4ade80; }
    .agent.busy { background: #7c2d12; color: #fb923c; }
    .log {
      font-family: monospace;
      font-size: 11px;
      background: #0a0a0a;
      padding: 10px;
      border-radius: 6px;
      max-height: 200px;
      overflow-y: auto;
      margin-top: 10px;
    }
    .log-line { padding: 2px 0; border-bottom: 1px solid #222; }
    .kill-btn {
      background: #dc2626;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: bold;
    }
    .kill-btn:hover { background: #b91c1c; }
  </style>
</head>
<body>
  <h1 style="margin-bottom: 20px;">⚡ MasterBuilder7 Dashboard</h1>
  
  <div class="grid">
    <div class="card">
      <h3>Budget Status</h3>
      <div id="budget-metric" class="metric">$0.00 / $100</div>
      <div class="bar"><div id="budget-bar" class="bar-fill" style="width: 0%"></div></div>
      <div id="budget-status" style="margin-top: 8px; font-size: 12px; color: #888;">OK</div>
    </div>
    
    <div class="card">
      <h3>Active Agents</h3>
      <div id="agents-metric" class="metric ok">0 / 12</div>
      <div class="agents" id="agent-list"></div>
    </div>
    
    <div class="card">
      <h3>System Status</h3>
      <div id="system-metric" class="metric ok">ONLINE</div>
      <div style="margin-top: 10px; font-size: 12px; color: #888;" id="system-details">
        All systems operational
      </div>
    </div>
    
    <div class="card">
      <h3>Emergency Control</h3>
      <button class="kill-btn" onclick="killSwitch()">🛑 KILL ALL</button>
      <div style="margin-top: 10px; font-size: 11px; color: #888;">
        Immediately stops all agents and deployments
      </div>
    </div>
    
    <div class="card" style="grid-column: 1 / -1;">
      <h3>Live Logs</h3>
      <div class="log" id="logs"></div>
    </div>
  </div>

  <script>
    const ws = new WebSocket('ws://localhost:3000/ws');
    
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      updateDashboard(data);
    };
    
    function updateDashboard(data) {
      // Budget
      const budgetEl = document.getElementById('budget-metric');
      const budgetBar = document.getElementById('budget-bar');
      const budgetStatus = document.getElementById('budget-status');
      
      budgetEl.textContent = \"\$\" + data.budget.spend.toFixed(2) + " / \$" + data.budget.limit;
      budgetBar.style.width = data.budget.percentage + "%";
      budgetStatus.textContent = data.budget.status.toUpperCase();
      
      // Color code
      budgetEl.className = "metric " + data.budget.status;
      budgetBar.className = "bar-fill " + data.budget.status;
      
      // Agents
      document.getElementById('agents-metric').textContent = 
        data.agents.active + " / " + data.agents.max;
      
      const agentList = document.getElementById('agent-list');
      agentList.innerHTML = data.agents.list.map(a => 
        '<span class="agent ' + a.state + '">' + a.name + '</span>'
      ).join('');
      
      // System
      const sysEl = document.getElementById('system-metric');
      sysEl.textContent = data.system.killed ? "KILLED" : "ONLINE";
      sysEl.className = "metric " + (data.system.killed ? "killed" : "ok");
      
      // Logs
      const logs = document.getElementById('logs');
      const line = document.createElement('div');
      line.className = 'log-line';
      line.textContent = new Date().toLocaleTimeString() + " " + data.log;
      logs.insertBefore(line, logs.firstChild);
      if (logs.children.length > 100) logs.removeChild(logs.lastChild);
    }
    
    function killSwitch() {
      if (!confirm('STOP ALL SYSTEMS?')) return;
      fetch('/api/kill', { method: 'POST' })
        .then(() => alert('Kill signal sent'));
    }
  </script>
</body>
</html>`;

class DashboardServer {
  private pg: Client;
  private redis: Redis;
  private subscribers: Set<any> = new Set();

  constructor() {
    this.pg = new Client({
      connectionString: process.env.POSTGRES_URL
    });
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  async start(): Promise<void> {
    await this.pg.connect();

    // Subscribe to Redis channels
    this.redis.subscribe('mb7:budget:update', 'mb7:agent:update', 'mb7:system:kill');
    
    this.redis.on('message', (channel, message) => {
      this.broadcast({ channel, data: JSON.parse(message) });
    });

    serve({
      port: parseInt(process.env.PORT || '3000'),
      fetch: async (req) => {
        const url = new URL(req.url);
        
        if (url.pathname === '/') {
          return new Response(HTML, { 
            headers: { 'Content-Type': 'text/html' } 
          });
        }
        
        if (url.pathname === '/api/status') {
          const status = await this.getStatus();
          return Response.json(status);
        }
        
        if (url.pathname === '/api/kill' && req.method === 'POST') {
          await this.redis.set('mb7:system:killed', 'true');
          await this.redis.publish('mb7:system:kill', JSON.stringify({
            reason: 'manual_kill',
            timestamp: new Date().toISOString()
          }));
          return Response.json({ killed: true });
        }
        
        if (url.pathname === '/ws') {
          // WebSocket upgrade handled by Bun
          return new Response('WebSocket endpoint', { status: 400 });
        }
        
        return new Response('Not found', { status: 404 });
      },
      websocket: {
        open: (ws) => {
          this.subscribers.add(ws);
          this.sendStatus(ws);
        },
        close: (ws) => {
          this.subscribers.delete(ws);
        }
      }
    });

    // Send updates every 5 seconds
    setInterval(() => this.broadcastStatus(), 5000);

    console.log('📊 Dashboard running on :3000');
  }

  private async getStatus() {
    const [budget, agents, system] = await Promise.all([
      this.getBudgetStatus(),
      this.getAgentStatus(),
      this.getSystemStatus()
    ]);

    return { budget, agents, system, log: 'Status updated' };
  }

  private async getBudgetStatus() {
    const result = await this.pg.query(
      `SELECT total_spend, percentage_used, status 
       FROM budget_status ORDER BY last_check DESC LIMIT 1`
    );

    if (result.rows.length === 0) {
      return { spend: 0, limit: 100, percentage: 0, status: 'ok' };
    }

    const row = result.rows[0];
    return {
      spend: parseFloat(row.total_spend),
      limit: 100,
      percentage: parseFloat(row.percentage_used),
      status: row.status
    };
  }

  private async getAgentStatus() {
    const agents = await this.redis.keys('mb7:agent:*');
    const list = [];
    
    for (const key of agents) {
      const data = await this.redis.hgetall(key);
      list.push({
        name: key.replace('mb7:agent:', ''),
        state: data.state || 'idle',
        task: data.task || 'none'
      });
    }

    return {
      active: list.filter(a => a.state === 'active').length,
      max: 12,
      list
    };
  }

  private async getSystemStatus() {
    const killed = await this.redis.get('mb7:system:killed');
    return { killed: killed === 'true' };
  }

  private async sendStatus(ws: any): Promise<void> {
    const status = await this.getStatus();
    ws.send(JSON.stringify(status));
  }

  private async broadcastStatus(): Promise<void> {
    const status = await this.getStatus();
    this.broadcast(status);
  }

  private broadcast(data: any): void {
    const message = JSON.stringify(data);
    for (const ws of this.subscribers) {
      try {
        ws.send(message);
      } catch (e) {
        // Client disconnected
      }
    }
  }
}

if (require.main === module) {
  const server = new DashboardServer();
  server.start().catch(console.error);
}

export { DashboardServer };