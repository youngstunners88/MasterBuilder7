#!/usr/bin/env bun
/**
 * TRI-ZO BRIDGE
 * Connects: Kofi Zo + Kimi APEX + Youngstunners Zo
 */

const ZO_KOFI = "https://kofi.zo.computer";
const ZO_KIMI = "http://35.235.249.249:8000";
const ZO_OTHER = "https://youngstunners.zo.space";

interface SystemStatus {
  name: string;
  url: string;
  status: 'online' | 'offline';
  agents?: number;
  last_ping?: string;
}

class TriZoBridge {
  private systems: SystemStatus[] = [
    { name: 'kofi-zo', url: ZO_KOFI, status: 'offline' },
    { name: 'kimi-apex', url: ZO_KIMI, status: 'offline' },
    { name: 'youngstunners-zo', url: ZO_OTHER, status: 'offline' }
  ];

  async checkAll(): Promise<SystemStatus[]> {
    for (const sys of this.systems) {
      try {
        const ctrl = new AbortController();
        setTimeout(() => ctrl.abort(), 5000);
        
        const res = await fetch(`${sys.url}/api/health`, { 
          signal: ctrl.signal 
        });
        
        sys.status = res.ok ? 'online' : 'offline';
        sys.last_ping = new Date().toISOString();
        
        // Try to get agent count
        try {
          const statusRes = await fetch(`${sys.url}/api/status`);
          const data = await statusRes.json();
          sys.agents = data.agents?.length || 0;
        } catch {}
        
      } catch {
        sys.status = 'offline';
      }
    }
    return this.systems;
  }

  async syncAgents(command: string, payload: any): Promise<any> {
    const results = [];
    
    for (const sys of this.systems.filter(s => s.status === 'online')) {
      try {
        const res = await fetch(`${sys.url}/api/agents/command`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command, payload, source: 'tri-zo-bridge' })
        });
        results.push({ system: sys.name, success: res.ok });
      } catch (e) {
        results.push({ system: sys.name, success: false, error: e.message });
      }
    }
    
    return { synchronized: results.filter(r => r.success).length, results };
  }

  async broadcast(message: any): Promise<void> {
    for (const sys of this.systems.filter(s => s.status === 'online')) {
      fetch(`${sys.url}/api/relay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...message, broadcast: true, timestamp: Date.now() })
      }).catch(() => {});
    }
  }
}

// CLI
if (import.meta.main) {
  const bridge = new TriZoBridge();
  
  console.log('🔥 TRI-ZO BRIDGE - Checking all systems...\n');
  
  const status = await bridge.checkAll();
  
  for (const sys of status) {
    const icon = sys.status === 'online' ? '🟢' : '🔴';
    const agents = sys.agents ? `(${sys.agents} agents)` : '';
    console.log(`${icon} ${sys.name}: ${sys.status.toUpperCase()} ${agents}`);
  }
  
  const online = status.filter(s => s.status === 'online').length;
  console.log(`\n📊 ${online}/${status.length} systems online`);
  
  if (online >= 2) {
    console.log('\n⚡ Synchronizing Elite Squad across all systems...');
    const sync = await bridge.syncAgents('deploy', { squad: 'elite', count: 8 });
    console.log(`✅ Synchronized to ${sync.synchronized} systems`);
  }
}

export { TriZoBridge };