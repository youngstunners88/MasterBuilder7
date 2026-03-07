#!/usr/bin/env python3
"""Obsidian Vault Analysis Tool"""
import argparse
import os
import re
from pathlib import Path
from collections import defaultdict

def find_md_files(vault_path: str) -> list:
    """Find all markdown files in vault"""
    return list(Path(vault_path).rglob("*.md"))

def extract_links(content: str) -> tuple:
    """Extract wiki-links and external links from content"""
    # Wiki-links: [[note name]] or [[note name|display]]
    wiki_links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)
    # External links: [text](url)
    ext_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    return wiki_links, ext_links

def find_orphans(vault_path: str) -> dict:
    """Find orphan notes (no incoming or outgoing links)"""
    md_files = find_md_files(vault_path)
    links_to = defaultdict(set)  # note -> set of notes linking TO it
    links_from = defaultdict(set)  # note -> set of notes linking FROM it
    
    for f in md_files:
        note_name = f.stem
        content = f.read_text(encoding='utf-8')
        wiki_links, _ = extract_links(content)
        
        for link in wiki_links:
            links_to[link].add(note_name)
            links_from[note_name].add(link)
    
    orphans = []
    for f in md_files:
        note_name = f.stem
        if not links_to[note_name] and not links_from[note_name]:
            orphans.append(str(f))
    
    return {"orphans": orphans, "links_to": dict(links_to), "links_from": dict(links_from)}

def find_broken_links(vault_path: str) -> list:
    """Find broken wiki-links (target doesn't exist)"""
    md_files = find_md_files(vault_path)
    existing_notes = {f.stem for f in md_files}
    broken = []
    
    for f in md_files:
        content = f.read_text(encoding='utf-8')
        wiki_links, _ = extract_links(content)
        
        for link in wiki_links:
            if link not in existing_notes:
                broken.append({"file": str(f), "broken_link": link})
    
    return broken

def normalize_tags(vault_path: str, tag_map: dict = None) -> dict:
    """Normalize tags (merge duplicates)"""
    if tag_map is None:
        # Auto-detect similar tags
        tag_map = {}
    
    md_files = find_md_files(vault_path)
    all_tags = defaultdict(list)
    
    for f in md_files:
        tags = re.findall(r'#(\w+)', f.read_text(encoding='utf-8'))
        for t in tags:
            all_tags[t.lower()].append(str(f))
    
    return {"tags": dict(all_tags), "files": len(md_files)}

def analyze_structure(vault_path: str) -> dict:
    """Analyze vault folder structure"""
    md_files = find_md_files(vault_path)
    folders = defaultdict(int)
    
    for f in md_files:
        folders[str(f.parent)] += 1
    
    return {
        "total_notes": len(md_files),
        "folders": dict(folders)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Obsidian Vault Audit")
    sub = parser.add_subparsers()
    
    o = sub.add_parser("orphans", help="Find orphan notes")
    o.add_argument("vault", help="Path to vault")
    o.set_defaults(func=lambda a: print(find_orphans(a.vault)))
    
    b = sub.add_parser("broken", help="Find broken links")
    b.add_argument("vault", help="Path to vault")
    b.set_defaults(func=lambda a: print(find_broken_links(a.vault)))
    
    n = sub.add_parser("tags", help="Analyze tags")
    n.add_argument("vault", help="Path to vault")
    n.set_defaults(func=lambda a: print(normalize_tags(a.vault)))
    
    s = sub.add_parser("structure", help="Analyze structure")
    s.add_argument("vault", help="Path to vault")
    s.set_defaults(func=lambda a: print(analyze_structure(a.vault)))
    
    a = sub.add_parser("audit", help="Full audit")
    a.add_argument("vault", help="Path to vault")
    a.set_defaults(func=lambda a: print({
        "structure": analyze_structure(a.vault),
        "orphans": len(find_orphans(a.vault)["orphans"]),
        "broken": len(find_broken_links(a.vault)),
        "tags": len(normalize_tags(a.vault)["tags"])
    }))
    
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()