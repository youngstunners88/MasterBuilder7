---
name: firecrawl-scanner
description: Scrape token launch pages and crypto sites for hidden alpha - contract addresses, launch dates, team info, and other data from the web.
metadata:
  author: youngstunners.zo.computer
---

# Firecrawl Scanner Skill

Scrape websites for alpha using Firecrawl web scraping.

## Setup
```bash
pip install firecrawl-py
```

Requires FIRECRAWL_API_KEY in environment variables.

## Usage
```python
from firecrawl import FirecrawlApp
import os
import re

app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

def scan_token_site(url):
    result = app.scrape_url(url, params={
        "formats": ["markdown", "html"],
        "onlyMainContent": True
    })
    return extract_alpha(result)

def extract_alpha(crawl_result):
    text = crawl_result.get("markdown", "")
    # Find contract addresses
    solana_addrs = re.findall(r'[A-Za-z0-9]{32,44}', text)
    eth_addrs = re.findall(r'0x[a-fA-F0-9]{40}', text)
    return {
        "solana_contracts": solana_addrs[:5],
        "ethereum_contracts": eth_addrs[:5],
        "raw": text[:3000]
    }
```