#!/usr/bin/env bun
/**
 * Memory Sync - Cross-Zo Memory Synchronisation
 * 
 * Usage:
 *   bun sync.ts push          - Push local memory to all nodes
 *   bun sync.ts pull <node>   - Pull memory from specific node
 *   bun sync.ts watch         - Watch for changes and sync
 *   bun sync.ts status        - Show sync status
 */

import { readdir, readFile, writeFile, stat } from "fs/promises";
import { join } from "path";

const MEMORY_PATH = "/home/workspace/EliteSquad/shared/memory";
const NODES = {
  kofi: "https://kofi.zo.space/api/memory",
  youngstunners: "https://youngstunners.zo.space/api/memory",
};

interface MemoryFile {
  path: string;
  content: string;
  lastModified: string;
  hash: string;
}

class MemorySync {
  private localPath: string;

  constructor(localPath: string = MEMORY_PATH) {
    this.localPath = localPath;
  }

  async getLocalMemory(): Promise<MemoryFile[]> {
    const files: MemoryFile[] = [];
    
    const walk = async (dir: string) => {
      const entries = await readdir(dir, { withFileTypes: true });
      for (const entry of entries) {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) {
          await walk(path);
        } else if (entry.name.endsWith(".md")) {
          const content = await readFile(path, "utf-8");
          const stats = await stat(path);
          
          files.push({
            path: path.replace(this.localPath, ""),
            content,
            lastModified: stats.mtime.toISOString(),
            hash: await this.hash(content),
          });
        }
      }
    };

    await walk(this.localPath);
    return files;
  }

  private async hash(content: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(content);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
  }

  async push(): Promise<void> {
    console.log("📤 Pushing local memory to all nodes...\n");
    
    const files = await this.getLocalMemory();
    console.log(`   Found ${files.length} memory files`);

    for (const [name, endpoint] of Object.entries(NODES)) {
      try {
        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source: "youngstunners.zo.computer",
            files,
            timestamp: new Date().toISOString(),
          }),
        });

        if (response.ok) {
          console.log(`   ✅ ${name}: Synced ${files.length} files`);
        } else {
          console.log(`   ❌ ${name}: HTTP ${response.status}`);
        }
      } catch (error) {
        console.log(`   ❌ ${name}: ${error instanceof Error ? error.message : "Failed"}`);
      }
    }
  }

  async pull(node: string): Promise<void> {
    console.log(`📥 Pulling memory from ${node}...\n`);
    
    const endpoint = NODES[node as keyof typeof NODES];
    if (!endpoint) {
      console.log(`   ❌ Unknown node: ${node}`);
      console.log(`   Available nodes: ${Object.keys(NODES).join(", ")}`);
      return;
    }

    try {
      const response = await fetch(`${endpoint}?source=youngstunners`, {
        method: "GET",
      });

      if (response.ok) {
        const data = await response.json();
        const files = data.files as MemoryFile[];
        
        console.log(`   Received ${files.length} files`);
        
        for (const file of files) {
          const localPath = join(this.localPath, file.path);
          await writeFile(localPath, file.content);
          console.log(`   ✅ ${file.path}`);
        }
      } else {
        console.log(`   ❌ HTTP ${response.status}`);
      }
    } catch (error) {
      console.log(`   ❌ ${error instanceof Error ? error.message : "Failed"}`);
    }
  }

  async status(): Promise<void> {
    console.log("📊 Memory Sync Status\n");
    
    const localFiles = await this.getLocalMemory();
    console.log(`   Local files: ${localFiles.length}`);
    
    for (const file of localFiles.slice(0, 10)) {
      console.log(`   - ${file.path} (${file.hash})`);
    }
    
    if (localFiles.length > 10) {
      console.log(`   ... and ${localFiles.length - 10} more`);
    }

    console.log("\n   Remote nodes:");
    for (const [name, endpoint] of Object.entries(NODES)) {
      try {
        const response = await fetch(`${endpoint}/health`, { method: "GET" });
        console.log(`   - ${name}: ${response.ok ? "✅ Online" : "❌ Offline"}`);
      } catch {
        console.log(`   - ${name}: ❌ Offline`);
      }
    }
  }

  async watch(intervalMs: number = 30000): Promise<void> {
    console.log("👁️ Watching for memory changes...\n");
    console.log(`   Checking every ${intervalMs / 1000}s`);
    console.log("   Press Ctrl+C to stop\n");

    let lastHash = "";

    const check = async () => {
      const files = await this.getLocalMemory();
      const combinedHash = files.map(f => f.hash).join("");
      
      if (combinedHash !== lastHash) {
        console.log(`[${new Date().toISOString()}] 📝 Memory changed, pushing...`);
        await this.push();
        lastHash = combinedHash;
      }
    };

    await check();
    setInterval(check, intervalMs);
  }
}

// CLI
const command = process.argv[2] || "status";
const arg = process.argv[3];

async function main() {
  const sync = new MemorySync();

  switch (command) {
    case "push":
      await sync.push();
      break;

    case "pull":
      await sync.pull(arg || "kofi");
      break;

    case "watch":
      await sync.watch(parseInt(arg) || 30000);
      break;

    case "status":
    default:
      await sync.status();
      break;
  }
}

main();
