#!/usr/bin/env bun
/**
 * APEX Fleet Dashboard
 * Real-time monitoring of 333-agent fleet
 */

import { Database } from "bun:sqlite";
import { serve } from "bun";

const DB_PATH = "/home/teacherchris37/MasterBuilder7/apex/fleet.db";
const db = new Database(DB_PATH);

// HTML Dashboard
const DASHBOARD_HTML = `
<!DOCTYPE html>
<html>
<head>
  <title>⚡ APEX Fleet Dashboard</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'JetBrains Mono', monospace;
      background: #0a0a0a;
      color: #00ff00;
      min-height: 100vh;
    }
    .header {
      background: linear-gradient(90deg, #00ff00, #00aa00);
      color: #000;
      padding: 20px;
      text-align: center;
    }
    .header h1 {
      font-size: 2.5em;
      text-transform: uppercase;
      letter-spacing: 5px;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 20px;
      padding: 20px;
    }
    .stat-card {
      background: #111;
      border: 1px solid #00ff00;
      padding: 20px;
      text-align: center;
      border-radius: 8px;
    }
    .stat-card h3 {
      color: #888;
      font-size: 0.9em;
      margin-bottom: 10px;
    }
    .stat-card .value {
      font-size: 3em;
      font-weight: bold;
    }
    .agents-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
      gap: 10px;
      padding: 20px;
    }
    .agent-box {
      background: #111;
      border: 2px solid #333;
      padding: 10px;
      text-align: center;
      font-size: 0.7em;
      border-radius: 4px;
      transition: all 0.3s;
    }
    .agent-box.running { border-color: #00ff00; background: #001100; }
    .agent-box.crashed { border-color: #ff0000; background: #110000; }
    .agent-box.spawning { border-color: #ffff00; background: #111100; }
    .agent-box.healing { border-color: #ff8800; background: #110800; animation: pulse 1s infinite; }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    .logs {
      background: #111;
      border: 1px solid #333;
      margin: 20px;
      padding: 20px;
      height: 300px;
      overflow-y: auto;
      font-size: 0.8em;
      border-radius: 8px;
    }
    .log-entry {
      margin: 2px 0;
      padding: 2px 0;
    }
    .universe-section {
      padding: 20px;
    }
    .universe-section h2 {
      color: #00aaff;
      margin-bottom: 15px;
      border-bottom: 2px solid #00aaff;
      padding-bottom: 10px;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>⚡ APEX FLEET COMMAND ⚓</h1>
    <p>333-Agent Autonomous Workforce | 24/7 Operation</p>
  </div>
  
  <div class="stats" id="stats">
    <div class="stat-card">
      <h3>TOTAL AGENTS</h3>
      <div class="value" id="total-agents">-</div>
    </div>
    <div class="stat-card">
      <h3>RUNNING</h3>
      <div class="value" id="running-agents">-</div>
    </div>
    <div class="stat-card">
      <h3>TASKS COMPLETED</h3>
      <div class="value" id="tasks-completed">-</div>
    </div>
    <div class="stat-card">
      <h3>FLEET HEALTH</h3>
      <div class="value" id="fleet-health">-</div>
    </div>
  </div>

  <div class="universe-section">
    <h2>🌌 PARALLEL UNIVERSES</h2>
    <div id="universes"></div>
  </div>

  <div class="universe-section">
    <h2>🤖 AGENT FLEET</h2>
    <div class="agents-grid" id="agents"></div>
  </div>

  <div class="logs" id="logs"></div>

  <script>
    async function updateDashboard() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        document.getElementById('total-agents').textContent = data.total;
        document.getElementById('running-agents').textContent = data.running;
        document.getElementById('tasks-completed').textContent = data.tasks;
        document.getElementById('fleet-health').textContent = data.health + '%';
        
        // Update agents
        const agentsDiv = document.getElementById('agents');
        agentsDiv.innerHTML = data.agents.map(a => \`
          <div class="agent-box \${a.status}">
            <div>\${a.id}</div>
            <div>\${a.type}</div>
            <div>\${a.status}</div>
          </div>
        \`).join('');
        
        // Update universes
        const univDiv = document.getElementById('universes');
        univDiv.innerHTML = Object.entries(data.universes).map(([name, count]) => \`
          <div class="stat-card" style="display:inline-block; margin:10px;">
            <h3>\${name}</h3>
            <div class="value">\${count}</div>
          </div>
        \`).join('');
        
      } catch (e) {
        console.error('Update failed:', e);
      }
    }
    
    // WebSocket for real-time logs
    const ws = new WebSocket('ws://localhost:7777/ws');
    ws.onmessage = (event) => {
      const logsDiv = document.getElementById('logs');
      const entry = document.createElement('div');
      entry.className = 'log-entry';
      entry.textContent = event.data;
      logsDiv.appendChild(entry);
      logsDiv.scrollTop = logsDiv.scrollHeight;
    };
    
    setInterval(updateDashboard, 1000);
    updateDashboard();
  </script>
</body>
</html>
`;

// API Server
const server = serve({
  port: 7777,
  routes: {
    "/": () => new Response(DASHBOARD_HTML, {
      headers: { "Content-Type": "text/html" }
    }),
    
    "/api/status": () => {
      const agents = db.prepare(`
        SELECT id, type, status, tasks_completed, universe FROM agents
      `).all() as any[];
      
      const stats = db.prepare(`
        SELECT 
          COUNT(*) as total,
          SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
          SUM(tasks_completed) as tasks
        FROM agents
      `).get() as any;
      
      const universes = db.prepare(`
        SELECT universe, COUNT(*) as count 
        FROM agents 
        WHERE universe IS NOT NULL
        GROUP BY universe
      `).all() as any[];
      
      const universeMap = universes.reduce((acc, u) => {
        acc[u.universe] = u.count;
        return acc;
      }, {} as Record<string, number>);
      
      return Response.json({
        total: stats.total || 0,
        running: stats.running || 0,
        tasks: stats.tasks || 0,
        health: stats.total ? Math.round((stats.running / stats.total) * 100) : 0,
        agents: agents,
        universes: universeMap
      });
    },
    
    "/api/agents/:id/logs": (req) => {
      const id = req.params.id;
      // In real impl, would fetch agent logs
      return Response.json({ agent: id, logs: [] });
    }
  },
  
  websocket: {
    message(ws, message) {
      // Echo back for now
      ws.send(message);
    },
    open(ws) {
      ws.send("[SYSTEM] Connected to APEX Fleet Dashboard");
    },
    close(ws) {
      console.log("Dashboard client disconnected");
    }
  }
});

console.log(`⚡ APEX Fleet Dashboard running at http://localhost:7777`);
console.log(`🎯 Monitor ${db.prepare("SELECT COUNT(*) as c FROM agents").get()?.c || 0} agents in real-time`);
