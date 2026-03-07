---
name: scrape-web
description: Extract content from websites. Use when user wants to scrape, crawl, or extract data from web pages.
metadata:
  author: youngstunners.zo.computer
---

# Scrape Web Skill

Extract content from web pages.

## Usage

### Quick read (static pages)
```
read_webpage(url="https://example.com")
```

### Interactive pages (login required, JS)
```
open_webpage(url="https://example.com")
view_webpage()
use_webpage(task="Click login, fill form...")
```

### Using Firecrawl (advanced)
```python
from firecrawl import FirecrawlApp
app = FirecrawlApp(api_key="fc-xxx")
result = app.scrape_url("https://example.com")
content = result.markdown
```

## Tools
- read_webpage: Fast text extraction
- open_webpage + view_webpage: For interactive pages
- use_webpage: For browser automation
- firecrawl (installed): For advanced scraping

## Examples
- "Read this article" → use read_webpage
- "Extract data from this dynamic page" → use open_webpage + use_webpage
- "Scrape multiple pages" → use Firecrawl