#!/usr/bin/env python3
"""Firecrawl Scanner - Scrape token/crypto sites for alpha"""
import os
import re
import sys

try:
    from firecrawl import FirecrawlApp
except ImportError:
    print("ERROR: firecrawl-py not installed. Run: pip install firecrawl-py")
    sys.exit(1)

class FirecrawlScanner:
    def __init__(self):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            print("ERROR: FIRECRAWL_API_KEY not set")
            sys.exit(1)
        self.app = FirecrawlApp(api_key=api_key)
    
    def scan(self, url):
        """Scrape a URL for alpha"""
        try:
            result = self.app.scrape_url(url, params={
                "formats": ["markdown", "html"],
                "onlyMainContent": True
            })
            return self._extract_alpha(result)
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_alpha(self, crawl_result):
        """Extract contracts, dates, and key info"""
        text = crawl_result.get("markdown", "")
        
        # Solana addresses (32-44 chars base58)
        solana = re.findall(r'[1-9A-HJ-NP-Za-km-z]{32,44}', text)
        # Ethereum addresses
        eth = re.findall(r'0x[a-fA-F0-9]{40}', text)
        # URLs
        urls = re.findall(r'https?://[^\s]+', text)
        
        return {
            "solana_addresses": list(set(solana))[:5],
            "ethereum_addresses": list(set(eth))[:5],
            "urls": list(set(urls))[:10],
            "content_preview": text[:2000]
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scanner.py <url>")
        sys.exit(1)
    
    scanner = FirecrawlScanner()
    result = scanner.scan(sys.argv[1])
    print(result)