#!/usr/bin/env python3
"""Basic usage example for Multi-Repo Intelligence."""

import sys
sys.path.insert(0, '..')

from src.indexer import RepoIndexer
from src.dependency_mapper import DependencyMapper
from src.graph import RepoGraph
from src.alerter import BreakingChangeAlerter

def main():
    print("=" * 60)
    print("Multi-Repo Intelligence - Basic Usage Example")
    print("=" * 60)
    
    # Initialize indexer
    indexer = RepoIndexer()
    
    # Add local repositories (adjust paths for your setup)
    print("\n1. Indexing repositories...")
    
    # Example: Add current directory as a repo
    try:
        indexer.add_local_repo("../../", name="robeetsday")
        print(f"   ✓ Indexed robeetsday")
    except Exception as e:
        print(f"   ⚠ Could not index: {e}")
    
    # Show statistics
    stats = indexer.get_stats()
    print(f"\n2. Index Statistics:")
    print(f"   Total repos: {stats['total_repos']}")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Languages: {stats['languages']}")
    
    # Map dependencies
    print("\n3. Mapping dependencies...")
    mapper = DependencyMapper(indexer)
    deps = mapper.map_dependencies()
    print(f"   Found {len(deps)} dependency links")
    
    # Check for circular dependencies
    cycles = mapper.get_circular_dependencies()
    if cycles:
        print(f"   ⚠ Found {len(cycles)} circular dependencies")
        for cycle in cycles:
            print(f"     {' → '.join(cycle)}")
    else:
        print("   ✓ No circular dependencies found")
    
    # Generate visualization
    print("\n4. Generating graph visualization...")
    graph = RepoGraph(indexer, mapper)
    graph.build_graph()
    
    # Save as Mermaid
    mermaid = graph.to_mermaid()
    with open("repo_diagram.mmd", "w") as f:
        f.write(mermaid)
    print("   ✓ Saved Mermaid diagram to repo_diagram.mmd")
    
    # Save as D3 JSON
    graph.save_d3_json("repo_graph.json")
    print("   ✓ Saved D3 JSON to repo_graph.json")
    
    # Generate dependency report
    print("\n5. Generating dependency report...")
    report = mapper.generate_dependency_report()
    with open("dependency_report.md", "w") as f:
        f.write(report)
    print("   ✓ Saved report to dependency_report.md")
    
    # Breaking change detection setup
    print("\n6. Setting up breaking change detection...")
    alerter = BreakingChangeAlerter(indexer, mapper)
    alerter.capture_baseline()
    print("   ✓ Baseline captured")
    
    # Save baseline
    alerter.save_baseline("baseline.json")
    print("   ✓ Baseline saved to baseline.json")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()