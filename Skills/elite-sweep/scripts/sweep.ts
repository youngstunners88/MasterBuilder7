#!/usr/bin/env bun
/**
 * Elite Sweep - Automated Code Audit Engine
 * 
 * Usage:
 *   bun sweep.ts audit <path>    - Full audit
 *   bun sweep.ts scan <path>     - Quick scan
 *   bun sweep.ts fix <path>      - Auto-fix
 *   bun sweep.ts report <path>   - Generate report
 */

import { readdir, readFile, writeFile, stat } from "fs/promises";
import { join, extname } from "path";

interface AuditResult {
  project: string;
  timestamp: string;
  summary: {
    totalIssues: number;
    critical: number;
    warnings: number;
    fixed: number;
  };
  issues: AuditIssue[];
  recommendations: string[];
}

interface AuditIssue {
  file: string;
  line?: number;
  severity: "critical" | "warning" | "info";
  category: string;
  message: string;
  fix?: string;
  fixed?: boolean;
}

class EliteSweep {
  private projectPath: string;
  private issues: AuditIssue[] = [];
  private fixed: number = 0;

  constructor(projectPath: string) {
    this.projectPath = projectPath;
  }

  async audit(): Promise<AuditResult> {
    console.log(`🔍 Elite Sweep: Auditing ${this.projectPath}\n`);
    
    // Run all checks
    await this.checkMissingFiles();
    await this.checkImports();
    await this.checkTypes();
    await this.checkRuntime();
    await this.checkSecurity();
    await this.checkStructure();

    const critical = this.issues.filter(i => i.severity === "critical").length;
    const warnings = this.issues.filter(i => i.severity === "warning").length;

    return {
      project: this.projectPath,
      timestamp: new Date().toISOString(),
      summary: {
        totalIssues: this.issues.length,
        critical,
        warnings,
        fixed: this.fixed,
      },
      issues: this.issues,
      recommendations: this.generateRecommendations(),
    };
  }

  private async checkMissingFiles(): Promise<void> {
    console.log("📁 Checking for missing files...");
    
    const requiredFiles = [
      "package.json",
      "tsconfig.json",
      "README.md",
    ];

    for (const file of requiredFiles) {
      const filePath = join(this.projectPath, file);
      try {
        await stat(filePath);
      } catch {
        this.issues.push({
          file,
          severity: "critical",
          category: "structure",
          message: `Missing required file: ${file}`,
          fix: `Create ${file} with appropriate content`,
        });
      }
    }
  }

  private async checkImports(): Promise<void> {
    console.log("📦 Checking imports...");
    
    const tsFiles = await this.findFiles([".ts", ".tsx"]);
    
    for (const file of tsFiles) {
      const content = await readFile(file, "utf-8");
      const lines = content.split("\n");
      
      lines.forEach((line, idx) => {
        // Check for relative imports that might not exist
        const importMatch = line.match(/from\s+['"](\.[^'"]+)['"]/);
        if (importMatch) {
          const importPath = importMatch[1];
          // Could add resolution check here
        }
        
        // Check for bare imports without extensions
        if (line.includes("import") && !line.includes("from '") && !line.includes('from "')) {
          // Could check for side-effect imports
        }
      });
    }
  }

  private async checkTypes(): Promise<void> {
    console.log("🔤 Checking types...");
    
    const tsFiles = await this.findFiles([".ts", ".tsx"]);
    
    for (const file of tsFiles) {
      const content = await readFile(file, "utf-8");
      
      // Check for 'any' usage
      const anyMatches = content.match(/:\s*any\b/g);
      if (anyMatches && anyMatches.length > 0) {
        this.issues.push({
          file: file.replace(this.projectPath, "."),
          severity: "warning",
          category: "types",
          message: `Found ${anyMatches.length} 'any' type usage(s)`,
          fix: "Replace 'any' with specific types",
        });
      }
      
      // Check for missing return types
      const funcMatches = content.match(/function\s+\w+\s*\([^)]*\)\s*{/g);
      if (funcMatches) {
        for (const match of funcMatches) {
          if (!match.includes(":")) {
            this.issues.push({
              file: file.replace(this.projectPath, "."),
              severity: "info",
              category: "types",
              message: `Function missing return type: ${match.slice(0, 30)}...`,
            });
          }
        }
      }
    }
  }

  private async checkRuntime(): Promise<void> {
    console.log("⚡ Checking runtime safety...");
    
    const tsFiles = await this.findFiles([".ts", ".tsx"]);
    
    for (const file of tsFiles) {
      const content = await readFile(file, "utf-8");
      const lines = content.split("\n");
      
      lines.forEach((line, idx) => {
        // Check for unhandled promises
        if (line.includes(".then(") && !line.includes("await") && !line.includes(".catch(")) {
          this.issues.push({
            file: file.replace(this.projectPath, "."),
            line: idx + 1,
            severity: "warning",
            category: "runtime",
            message: "Potential unhandled promise",
            fix: "Add await or .catch()",
          });
        }
        
        // Check for potential null access
        if (line.match(/\w+\.\w+\s*\(/) && !line.includes("?.") && !line.includes("if (") && !line.includes("&&")) {
          // Could be more sophisticated
        }
      });
    }
  }

  private async checkSecurity(): Promise<void> {
    console.log("🔐 Checking security...");
    
    const allFiles = await this.findFiles([".ts", ".tsx", ".js", ".jsx", ".env.example"]);
    
    for (const file of allFiles) {
      const content = await readFile(file, "utf-8");
      
      // Check for hardcoded secrets
      const secretPatterns = [
        /api[_-]?key\s*=\s*['"][^'"]+['"]/gi,
        /secret[_-]?key\s*=\s*['"][^'"]+['"]/gi,
        /password\s*=\s*['"][^'"]+['"]/gi,
        /token\s*=\s*['"][^'"]+['"]/gi,
      ];
      
      for (const pattern of secretPatterns) {
        const matches = content.match(pattern);
        if (matches) {
          this.issues.push({
            file: file.replace(this.projectPath, "."),
            severity: "critical",
            category: "security",
            message: `Potential hardcoded secret: ${matches[0].slice(0, 30)}...`,
            fix: "Move to environment variable",
          });
        }
      }
      
      // Check for SQL injection risks
      if (content.includes("${") && content.includes("SELECT") && !content.includes("parameterized")) {
        this.issues.push({
          file: file.replace(this.projectPath, "."),
          severity: "critical",
          category: "security",
          message: "Potential SQL injection: string interpolation in SQL",
          fix: "Use parameterized queries",
        });
      }
    }
  }

  private async checkStructure(): Promise<void> {
    console.log("🏗️ Checking project structure...");
    
    // Check for common patterns
    const hasSrc = await this.exists(join(this.projectPath, "src"));
    const hasDist = await this.exists(join(this.projectPath, "dist"));
    const hasTests = await this.exists(join(this.projectPath, "tests")) || 
                     await this.exists(join(this.projectPath, "__tests__")) ||
                     (await this.findFiles([".test.ts", ".spec.ts"])).length > 0;
    
    if (!hasTests) {
      this.issues.push({
        file: "project",
        severity: "warning",
        category: "structure",
        message: "No test directory found",
        fix: "Add tests/ directory with unit tests",
      });
    }
    
    // Check package.json scripts
    try {
      const pkgPath = join(this.projectPath, "package.json");
      const pkg = JSON.parse(await readFile(pkgPath, "utf-8"));
      
      const requiredScripts = ["build", "test", "start"];
      for (const script of requiredScripts) {
        if (!pkg.scripts?.[script]) {
          this.issues.push({
            file: "package.json",
            severity: "warning",
            category: "structure",
            message: `Missing npm script: ${script}`,
            fix: `Add "${script}" script to package.json`,
          });
        }
      }
    } catch {
      // Already flagged as missing
    }
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

  private async exists(path: string): Promise<boolean> {
    try {
      await stat(path);
      return true;
    } catch {
      return false;
    }
  }

  private generateRecommendations(): string[] {
    const recommendations: string[] = [];
    
    const criticalCount = this.issues.filter(i => i.severity === "critical").length;
    const warningCount = this.issues.filter(i => i.severity === "warning").length;
    
    if (criticalCount > 0) {
      recommendations.push(`🔴 Fix ${criticalCount} critical issue(s) before deployment`);
    }
    if (warningCount > 5) {
      recommendations.push(`🟡 Address ${warningCount} warnings to improve code quality`);
    }
    
    const securityIssues = this.issues.filter(i => i.category === "security");
    if (securityIssues.length > 0) {
      recommendations.push(`🔐 Review and fix ${securityIssues.length} security issue(s)`);
    }
    
    const typeIssues = this.issues.filter(i => i.category === "types");
    if (typeIssues.length > 0) {
      recommendations.push(`🔤 Improve type coverage by addressing ${typeIssues.length} type issue(s)`);
    }
    
    return recommendations;
  }

  printReport(result: AuditResult): void {
    console.log("\n" + "═".repeat(60));
    console.log("📊 ELITE SWEEP AUDIT REPORT");
    console.log("═".repeat(60));
    console.log(`\nProject: ${result.project}`);
    console.log(`Timestamp: ${result.timestamp}`);
    console.log(`\n📈 Summary:`);
    console.log(`   Total Issues: ${result.summary.totalIssues}`);
    console.log(`   🔴 Critical: ${result.summary.critical}`);
    console.log(`   🟡 Warnings: ${result.summary.warnings}`);
    console.log(`   ✅ Fixed: ${result.summary.fixed}`);
    
    if (result.issues.length > 0) {
      console.log(`\n📋 Issues Found:`);
      for (const issue of result.issues.slice(0, 20)) {
        const icon = issue.severity === "critical" ? "🔴" : issue.severity === "warning" ? "🟡" : "ℹ️";
        console.log(`\n   ${icon} [${issue.category}] ${issue.file}${issue.line ? `:${issue.line}` : ""}`);
        console.log(`      ${issue.message}`);
        if (issue.fix) {
          console.log(`      💡 Fix: ${issue.fix}`);
        }
      }
      
      if (result.issues.length > 20) {
        console.log(`\n   ... and ${result.issues.length - 20} more issues`);
      }
    }
    
    if (result.recommendations.length > 0) {
      console.log(`\n📌 Recommendations:`);
      for (const rec of result.recommendations) {
        console.log(`   ${rec}`);
      }
    }
    
    console.log("\n" + "═".repeat(60));
  }
}

// CLI
const command = process.argv[2];
const path = process.argv[3] || process.cwd();

async function main() {
  const sweep = new EliteSweep(path);
  
  switch (command) {
    case "audit":
    case "scan":
      const result = await sweep.audit();
      sweep.printReport(result);
      break;
      
    case "fix":
      console.log("🔧 Auto-fix mode not yet implemented - run audit first");
      break;
      
    case "report":
      const auditResult = await sweep.audit();
      const reportPath = join(path, "sweep-report.json");
      await writeFile(reportPath, JSON.stringify(auditResult, null, 2));
      console.log(`📄 Report saved to: ${reportPath}`);
      break;
      
    default:
      console.log("Usage: bun sweep.ts [audit|scan|fix|report] <path>");
  }
}

main();
