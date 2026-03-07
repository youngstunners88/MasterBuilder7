#!/usr/bin/env bun
/**
 * APEX Fleet Launcher
 * 24/7 Persistent Service Entry Point
 */

import { spawn } from "bun";

console.log(`
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ⚡ APEX FLEET - 333 AGENT AUTONOMOUS WORKFORCE          ║
║                                                              ║
║     24/7 Operation | Self-Healing | Parallel Universe       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
`);

// Start Fleet Manager
const fleetProcess = spawn({
  cmd: ['bun', '/home/teacherchris37/MasterBuilder7/apex/fleet-manager.ts', 'spawn'],
  stdout: 'inherit',
  stderr: 'inherit',
});

console.log(`🚀 Fleet Manager PID: ${fleetProcess.pid}`);

// Start Dashboard
const dashboardProcess = spawn({
  cmd: ['bun', '/home/teacherchris37/MasterBuilder7/apex/dashboard.ts'],
  stdout: 'inherit',
  stderr: 'inherit',
});

console.log(`📊 Dashboard PID: ${dashboardProcess.pid}`);
console.log(`\n🔗 Access dashboard at: http://localhost:7777`);
console.log(`📋 Access via Zo Space: https://kofi.zo.space/fleet (if configured)\n`);

// Keep alive
await Promise.all([
  fleetProcess.exited,
  dashboardProcess.exited
]);
