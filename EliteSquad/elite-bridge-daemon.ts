#!/usr/bin/env bun

import { KOFI_ZO, YOUNGSTUNNERS_ZO, KIMI_HOST } from './config.js';

let heartbeatCount = 0;

async function sendHeartbeat() {
  heartbeatCount++;
  const timestamp = new Date().toISOString();
  
  console.log(`\n🔗 [${timestamp}] Heartbeat #${heartbeatCount}`);
  console.log("=".repeat(50));
  
  // Send heartbeat to Kofi
  try {
    const kofiRes = await fetch(`https://${KOFI_ZO}/api/kimi-bridge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        type: "heartbeat",
        from: "youngstunners",
        status: "online",
        agents_active: 8,
        projects: ["ihhashi", "nexus", "diamonds", "elitesquad"],
        timestamp
      })
    });
    const kofiData = await kofiRes.json();
    console.log("✅ Kofi:", kofiData.status || "synced");
  } catch (e) {
    console.log("❌ Kofi: unreachable");
  }
  
  // Update my bridge status
  try {
    const myRes = await fetch(`https://${YOUNGSTUNNERS_ZO}/api/elite-bridge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        type: "heartbeat",
        from: "youngstunners",
        kimi_status: "checking",
        kofi_status: "active"
      })
    });
    console.log("✅ My Bridge: updated");
  } catch (e) {
    console.log("❌ My Bridge: error");
  }
  
  // Check Kimi CLI (may be offline)
  try {
    const kimiRes = await fetch(`http://${KIMI_HOST}/api/v1/health`, {
      signal: AbortSignal.timeout(5000)
    });
    const kimiData = await kimiRes.json();
    console.log("✅ Kimi CLI:", kimiData.status || "online");
  } catch (e) {
    console.log("⏳ Kimi CLI: offline/behind firewall");
  }
  
  console.log("=".repeat(50));
  console.log("🤖 8 Agents Active | Next heartbeat in 60s");
}

// Initial sync
sendHeartbeat();

// Continuous sync every 60 seconds
setInterval(sendHeartbeat, 60000);

console.log("\n🚀 Elite Bridge Daemon Started");
console.log("📍 youngstunners.zo.computer → kofi.zo.space");
console.log("⏰ Heartbeat: every 60 seconds");
console.log("Press Ctrl+C to stop\n");
