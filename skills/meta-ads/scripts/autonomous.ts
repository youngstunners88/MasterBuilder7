#!/usr/bin/env bun
/**
 * Autonomous Meta Ads Manager
 * 
 * Runs the full daily cycle:
 * 1. Health check
 * 2. Fatigue detection
 * 3. Auto-pause bleeders
 * 4. Budget optimization
 * 5. Copy generation
 * 6. Morning brief (Telegram)
 * 7. GitHub issues for findings
 * 
 * Usage:
 *   bun autonomous.ts                    # Dry run (preview only)
 *   bun autonomous.ts --execute          # Execute changes
 *   bun autonomous.ts --execute --telegram # Send Telegram brief
 */

import { spawn } from "child_process";

const SCRIPTS_DIR = import.meta.dir;

interface StepResult {
  name: string;
  success: boolean;
  output: string;
  findings?: any[];
}

async function runScript(script: string, args: string[] = []): Promise<StepResult> {
  return new Promise((resolve) => {
    const proc = spawn("bun", [script, ...args], {
      cwd: SCRIPTS_DIR,
      stdio: "pipe",
    });

    let output = "";
    proc.stdout.on("data", (data) => (output += data.toString()));
    proc.stderr.on("data", (data) => (output += data.toString()));

    proc.on("close", (code) => {
      resolve({
        name: script.replace(".ts", "").replace(/^.*\//, ""),
        success: code === 0,
        output,
      });
    });
  });
}

async function createGitHubIssue(type: string, title: string, body: string): Promise<void> {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    console.log("  ⚠️ GITHUB_TOKEN not set, skipping issue creation");
    return;
  }

  const result = await runScript("github-issues.ts", [
    "--type", type,
    "--title", title,
    "--body", body,
  ]);

  if (result.success) {
    console.log(`  📝 Created GitHub issue`);
  } else {
    console.log(`  ⚠️ Failed to create issue: ${result.output.slice(0, 100)}`);
  }
}

async function run() {
  const args = process.argv.slice(2);
  const execute = args.includes("--execute");
  const sendTelegram = args.includes("--telegram");

  console.log("═══════════════════════════════════════════════════════");
  console.log("🤖 iHhashi Meta Ads Autonomous Manager");
  console.log("═══════════════════════════════════════════════════════\n");
  console.log(`Mode: ${execute ? "EXECUTE" : "DRY RUN (preview only)"}`);
  console.log(`Time: ${new Date().toISOString()}\n`);

  const execArgs = execute ? ["--execute"] : [];
  const telegramArgs = sendTelegram ? ["--telegram"] : [];

  const steps: StepResult[] = [];

  // Step 1: Health Check
  console.log("📊 Step 1: Health Check");
  const health = await runScript("health-check.ts", execArgs);
  steps.push(health);
  console.log(health.success ? "  ✅ Complete\n" : `  ❌ Failed: ${health.output.slice(0, 100)}\n`);

  // Step 2: Fatigue Detection
  console.log("😴 Step 2: Fatigue Detection");
  const fatigue = await runScript("fatigue-detector.ts", execArgs);
  steps.push(fatigue);
  console.log(fatigue.success ? "  ✅ Complete\n" : `  ❌ Failed\n`);

  // Create GitHub issues for fatigued ads
  if (fatigue.success && execute) {
    // Parse fatigue findings from output
    const fatigueMatches = fatigue.output.matchAll(/Campaign: (.+?) \((.+?)\).*?Frequency: ([\d.]+)/g);
    for (const match of fatigueMatches) {
      await createGitHubIssue(
        "fatigue",
        `Fatigued Ad: ${match[1]}`,
        `Campaign ${match[1]} (${match[2]}) has frequency ${match[3]} (> 3.5 threshold). Consider refreshing creative or expanding audience.`
      );
    }
  }

  // Step 3: Auto-Pause
  console.log("⏸️ Step 3: Auto-Pause Bleeders");
  const pause = await runScript("auto-pause.ts", execArgs);
  steps.push(pause);
  console.log(pause.success ? "  ✅ Complete\n" : `  ❌ Failed\n`);

  // Create GitHub issues for paused campaigns
  if (pause.success && execute) {
    const pauseMatches = pause.output.matchAll(/Paused: (.+?) \((.+?)\).*?CPA: \$([\d.]+)/g);
    for (const match of pauseMatches) {
      await createGitHubIssue(
        "critical",
        `Paused Bleeder: ${match[1]}`,
        `Campaign ${match[1]} (${match[2]}) auto-paused. CPA was $${match[3]} (> 2.5x target). Review and fix or archive.`
      );
    }
  }

  // Step 4: Budget Optimization
  console.log("💰 Step 4: Budget Optimization");
  const budget = await runScript("budget-optimizer.ts", execArgs);
  steps.push(budget);
  console.log(budget.success ? "  ✅ Complete\n" : `  ❌ Failed\n`);

  // Step 5: Copy Generation
  console.log("✍️ Step 5: Copy Generation");
  const copy = await runScript("copy-generator.ts");
  steps.push(copy);
  console.log(copy.success ? "  ✅ Complete\n" : `  ❌ Failed\n`);

  // Create GitHub issue for copy suggestions
  if (copy.success && execute && copy.output.includes("Generated:")) {
    await createGitHubIssue(
      "copy",
      "New Ad Copy Suggestions",
      `New ad copy variations generated from top performers.\n\n${copy.output}`
    );
  }

  // Step 6: Morning Brief
  if (sendTelegram) {
    console.log("📱 Step 6: Morning Brief (Telegram)");
    const brief = await runScript("morning-brief.ts", ["--telegram"]);
    steps.push(brief);
    console.log(brief.success ? "  ✅ Sent\n" : `  ❌ Failed\n`);
  }

  // Summary
  console.log("═══════════════════════════════════════════════════════");
  console.log("📋 SUMMARY");
  console.log("═══════════════════════════════════════════════════════\n");

  const succeeded = steps.filter((s) => s.success).length;
  const failed = steps.filter((s) => !s.success).length;

  console.log(`✅ Succeeded: ${succeeded}`);
  console.log(`❌ Failed: ${failed}`);

  if (!execute) {
    console.log(`\n⚠️ DRY RUN - No changes made`);
    console.log(`Run with --execute to apply changes`);
  }

  console.log(`\n📂 View issues: https://github.com/youngstunners88/ihhashi/issues?q=is:issue+is:open+label:ads`);
  console.log(`\n✨ Done!\n`);
}

run().catch((error) => {
  console.error("❌ Error:", error.message);
  process.exit(1);
});
