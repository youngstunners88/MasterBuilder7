#!/usr/bin/env bun
/**
 * Pattern Extractor - Automatic Pattern Extraction from Codebases
 * 
 * Usage:
 *   bun extract.ts analyze <path>
 *   bun extract.ts code <path>
 *   bun extract.ts architecture <path>
 *   bun extract.ts anti-patterns <path>
 *   bun extract.ts export <path> <output>
 */

import { readdir, readFile, writeFile, stat, mkdir } from "fs/promises";
import { join, extname, basename } from "path";

interface Pattern {
  type: "code" | "architecture" | "process" | "anti-pattern";
  name: string;
  description: string;
  occurrences: number;
  files: string[];
  template?: string;
  severity?: "low" | "medium" | "high";
}

interface ExtractionResult {
  project: string;
  timestamp: string;
  patterns: Pattern[];
  antiPatterns: Pattern[];
  statistics: {
    filesAnalyzed: number;
    patternsFound: number;
    antiPatternsFound: number;
  };
}

class PatternExtractor {
  private projectPath: string;
  private patterns: Pattern[] = [];
  private antiPatterns: Pattern[] = [];
  private filesAnalyzed: number = 0;

  constructor(projectPath: string) {
    this.projectPath = projectPath;
  }

  async analyze(): Promise<ExtractionResult> {
    console.log(`🔍 Analyzing patterns in ${this.projectPath}\n`);
    
    const files = await this.findFiles([".ts", ".tsx", ".js", ".jsx", ".py"]);
    console.log(`   Found ${files.length} files to analyze\n`);

    for (const file of files) {
      await this.analyzeFile(file);
      this.filesAnalyzed++;
    }

    return {
      project: basename(this.projectPath),
      timestamp: new Date().toISOString(),
      patterns: this.patterns,
      antiPatterns: this.antiPatterns,
      statistics: {
        filesAnalyzed: this.filesAnalyzed,
        patternsFound: this.patterns.length,
        antiPatternsFound: this.antiPatterns.length,
      },
    };
  }

  private async analyzeFile(filePath: string): Promise<void> {
    const content = await readFile(filePath, "utf-8");
    const relativePath = filePath.replace(this.projectPath, ".");

    // Code patterns
    this.detectCodePatterns(content, relativePath);
    
    // Architecture patterns
    this.detectArchitecturePatterns(content, relativePath);
    
    // Anti-patterns
    this.detectAntiPatterns(content, relativePath);
  }

  private detectCodePatterns(content: string, filePath: string): void {
    // Pattern: SOUL loading
    if (content.includes("SOUL.md") && content.includes("loadSOUL")) {
      this.addPattern({
        type: "code",
        name: "SOUL Loading Pattern",
        description: "Loads agent identity from SOUL.md file",
        occurrences: 1,
        files: [filePath],
        template: this.extractTemplate(content, "SOUL"),
      });
    }

    // Pattern: Error handling
    const tryCatchMatches = content.match(/try\s*\{/g);
    if (tryCatchMatches && tryCatchMatches.length > 2) {
      this.addPattern({
        type: "code",
        name: "Defensive Error Handling",
        description: "Multiple try-catch blocks for error safety",
        occurrences: tryCatchMatches.length,
        files: [filePath],
      });
    }

    // Pattern: Async/await
    const asyncMatches = content.match(/async\s+\w+\s*\(/g);
    if (asyncMatches && asyncMatches.length > 3) {
      this.addPattern({
        type: "code",
        name: "Async-First Design",
        description: "Heavy use of async/await pattern",
        occurrences: asyncMatches.length,
        files: [filePath],
      });
    }

    // Pattern: Type definitions
    const interfaceMatches = content.match(/interface\s+\w+/g);
    if (interfaceMatches && interfaceMatches.length > 2) {
      this.addPattern({
        type: "code",
        name: "Interface-Driven Development",
        description: "Strong typing with TypeScript interfaces",
        occurrences: interfaceMatches.length,
        files: [filePath],
      });
    }

    // Pattern: Dependency injection
    if (content.includes("constructor(") && content.includes("private")) {
      this.addPattern({
        type: "code",
        name: "Dependency Injection",
        description: "Constructor-based dependency injection",
        occurrences: 1,
        files: [filePath],
      });
    }
  }

  private detectArchitecturePatterns(content: string, filePath: string): void {
    // Pattern: Agent pattern
    if (content.includes("class Agent") || content.includes("extends Agent")) {
      this.addPattern({
        type: "architecture",
        name: "Agent Pattern",
        description: "Autonomous agent with identity and memory",
        occurrences: 1,
        files: [filePath],
      });
    }

    // Pattern: Bridge pattern
    if (content.includes("bridge") && content.includes("sync")) {
      this.addPattern({
        type: "architecture",
        name: "Bridge Pattern",
        description: "Cross-system communication bridge",
        occurrences: 1,
        files: [filePath],
      });
    }

    // Pattern: Memory pattern
    if (content.includes("memory") && (content.includes("save") || content.includes("load"))) {
      this.addPattern({
        type: "architecture",
        name: "Persistent Memory Pattern",
        description: "State persistence to filesystem",
        occurrences: 1,
        files: [filePath],
      });
    }

    // Pattern: Pipeline pattern
    if (content.includes("Promise.all") && content.includes("await")) {
      this.addPattern({
        type: "architecture",
        name: "Parallel Pipeline",
        description: "Concurrent execution of independent tasks",
        occurrences: 1,
        files: [filePath],
      });
    }
  }

  private detectAntiPatterns(content: string, filePath: string): void {
    // Anti-pattern: Missing error handling
    const awaitMatches = content.match(/await\s+\w+/g);
    const tryMatches = content.match(/try\s*\{/g);
    if (awaitMatches && awaitMatches.length > 2 && (!tryMatches || tryMatches.length < 1)) {
      this.antiPatterns.push({
        type: "anti-pattern",
        name: "Missing Error Handling",
        description: "Multiple awaits without try-catch protection",
        occurrences: awaitMatches.length,
        files: [filePath],
        severity: "medium",
      });
    }

    // Anti-pattern: Hardcoded values
    const hardcodedMatches = content.match(/(?:url|endpoint|api|host)\s*[=:]\s*['"]https?:\/\/[^'"]+['"]/gi);
    if (hardcodedMatches && hardcodedMatches.length > 2) {
      this.antiPatterns.push({
        type: "anti-pattern",
        name: "Hardcoded URLs",
        description: "Multiple hardcoded URLs should be configurable",
        occurrences: hardcodedMatches.length,
        files: [filePath],
        severity: "low",
      });
    }

    // Anti-pattern: Any type
    const anyMatches = content.match(/:\s*any\b/g);
    if (anyMatches && anyMatches.length > 3) {
      this.antiPatterns.push({
        type: "anti-pattern",
        name: "Excessive 'any' Usage",
        description: "Too many 'any' types reduce type safety",
        occurrences: anyMatches.length,
        files: [filePath],
        severity: "medium",
      });
    }

    // Anti-pattern: Console.log in production code
    const consoleMatches = content.match(/console\.(log|debug|info)/g);
    if (consoleMatches && consoleMatches.length > 5) {
      this.antiPatterns.push({
        type: "anti-pattern",
        name: "Excessive Console Logging",
        description: "Many console.log statements - consider proper logging",
        occurrences: consoleMatches.length,
        files: [filePath],
        severity: "low",
      });
    }

    // Anti-pattern: God function
    const lines = content.split("\n");
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.match(/(?:async\s+)?function\s+\w+|const\s+\w+\s*=\s*(?:async\s+)?\(/)) {
        let funcLength = 0;
        let braceCount = 0;
        let j = i;
        
        while (j < lines.length) {
          braceCount += (lines[j].match(/{/g) || []).length;
          braceCount -= (lines[j].match(/}/g) || []).length;
          funcLength++;
          j++;
          if (braceCount === 0 && j > i) break;
        }
        
        if (funcLength > 50) {
          this.antiPatterns.push({
            type: "anti-pattern",
            name: "God Function",
            description: `Function exceeds 50 lines (${funcLength} lines)`,
            occurrences: 1,
            files: [filePath],
            severity: "high",
          });
        }
      }
    }
  }

  private addPattern(pattern: Pattern): void {
    const existing = this.patterns.find(
      p => p.type === pattern.type && p.name === pattern.name
    );
    
    if (existing) {
      existing.occurrences += pattern.occurrences;
      existing.files.push(...pattern.files);
    } else {
      this.patterns.push(pattern);
    }
  }

  private extractTemplate(content: string, keyword: string): string {
    const lines = content.split("\n");
    const startIdx = lines.findIndex(l => l.includes(keyword));
    if (startIdx === -1) return "";
    
    const template: string[] = [];
    let braceCount = 0;
    let started = false;
    
    for (let i = startIdx; i < lines.length && i < startIdx + 30; i++) {
      const line = lines[i];
      if (line.includes("{")) {
        braceCount++;
        started = true;
      }
      if (line.includes("}")) braceCount--;
      
      template.push(line);
      
      if (started && braceCount === 0) break;
    }
    
    return template.join("\n");
  }

  private async findFiles(extensions: string[]): Promise<string[]> {
    const files: string[] = [];
    
    const walk = async (dir: string) => {
      try {
        const entries = await readdir(dir, { withFileTypes: true });
        for (const entry of entries) {
          const path = join(dir, entry.name);
          if (entry.isDirectory() && !entry.name.startsWith(".") && entry.name !== "node_modules") {
            await walk(path);
          } else if (entry.isFile()) {
            const ext = extname(entry.name);
            if (extensions.includes(ext)) {
              files.push(path);
            }
          }
        }
      } catch {}
    };
    
    await walk(this.projectPath);
    return files;
  }

  printReport(result: ExtractionResult): void {
    console.log("\n" + "═".repeat(65));
    console.log("📊 PATTERN EXTRACTION REPORT");
    console.log("═".repeat(65));
    console.log(`\nProject: ${result.project}`);
    console.log(`Timestamp: ${result.timestamp}`);
    console.log(`\n📈 Statistics:`);
    console.log(`   Files analyzed: ${result.statistics.filesAnalyzed}`);
    console.log(`   Patterns found: ${result.statistics.patternsFound}`);
    console.log(`   Anti-patterns found: ${result.statistics.antiPatternsFound}`);

    if (result.patterns.length > 0) {
      console.log(`\n✅ Patterns Found:`);
      for (const p of result.patterns) {
        console.log(`\n   [${p.type}] ${p.name}`);
        console.log(`   ${p.description}`);
        console.log(`   Occurrences: ${p.occurrences} in ${p.files.length} file(s)`);
      }
    }

    if (result.antiPatterns.length > 0) {
      console.log(`\n⚠️ Anti-Patterns Found:`);
      for (const p of result.antiPatterns) {
        const severity = p.severity === "high" ? "🔴" : p.severity === "medium" ? "🟡" : "🟢";
        console.log(`\n   ${severity} [${p.severity}] ${p.name}`);
        console.log(`   ${p.description}`);
        console.log(`   Occurrences: ${p.occurrences} in ${p.files.length} file(s)`);
      }
    }

    console.log("\n" + "═".repeat(65));
  }

  async export(outputDir: string): Promise<void> {
    await mkdir(outputDir, { recursive: true });
    
    const result = await this.analyze();
    
    // Export JSON
    await writeFile(
      join(outputDir, "patterns.json"),
      JSON.stringify(result, null, 2)
    );
    
    // Export markdown
    let md = `# Pattern Report: ${result.project}\n\n`;
    md += `Generated: ${result.timestamp}\n\n`;
    
    md += `## Statistics\n\n`;
    md += `- Files analyzed: ${result.statistics.filesAnalyzed}\n`;
    md += `- Patterns found: ${result.statistics.patternsFound}\n`;
    md += `- Anti-patterns found: ${result.statistics.antiPatternsFound}\n\n`;
    
    if (result.patterns.length > 0) {
      md += `## Patterns\n\n`;
      for (const p of result.patterns) {
        md += `### ${p.name}\n\n`;
        md += `**Type:** ${p.type}\n\n`;
        md += `${p.description}\n\n`;
        md += `**Occurrences:** ${p.occurrences}\n\n`;
      }
    }
    
    if (result.antiPatterns.length > 0) {
      md += `## Anti-Patterns\n\n`;
      for (const p of result.antiPatterns) {
        md += `### ${p.name} (${p.severity})\n\n`;
        md += `${p.description}\n\n`;
      }
    }
    
    await writeFile(join(outputDir, "PATTERNS.md"), md);
    
    console.log(`\n✅ Patterns exported to ${outputDir}`);
  }
}

// CLI
const command = process.argv[2];
const path = process.argv[3] || process.cwd();
const output = process.argv[4];

async function main() {
  const extractor = new PatternExtractor(path);

  switch (command) {
    case "analyze":
      const result = await extractor.analyze();
      extractor.printReport(result);
      break;

    case "code":
    case "architecture":
      const specific = await extractor.analyze();
      const filtered = specific.patterns.filter(p => p.type === command);
      console.log(`\n${filtered.length} ${command} patterns found:\n`);
      for (const p of filtered) {
        console.log(`  - ${p.name}: ${p.description}`);
      }
      break;

    case "anti-patterns":
      const antiResult = await extractor.analyze();
      console.log(`\n${antiResult.antiPatterns.length} anti-patterns found:\n`);
      for (const p of antiResult.antiPatterns) {
        const icon = p.severity === "high" ? "🔴" : p.severity === "medium" ? "🟡" : "🟢";
        console.log(`  ${icon} ${p.name}: ${p.description}`);
      }
      break;

    case "export":
      if (!output) {
        console.log("Usage: bun extract.ts export <path> <output-dir>");
        break;
      }
      await extractor.export(output);
      break;

    default:
      console.log("Usage: bun extract.ts [analyze|code|architecture|anti-patterns|export] <path>");
  }
}

main();
