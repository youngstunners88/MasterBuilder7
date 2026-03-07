---
name: find-local-leads
description: Find local businesses without websites using Google Maps - for lead generation and outreach
usage: |
  ## When to use
  - User wants to find local businesses without websites
  - Lead generation for web design/services
  - Research for local business outreach

  ## Categories to search
  - hair salons, plumbers, auto repair, restaurants, dentists, etc.

  ## Process
  1. Use maps_search with "no website" query
  2. Open Google Maps browser and iterate through results
  3. Collect: Name, Phone, Address, Category
  4. Filter: Only businesses WITHOUT websites

  ## Output
  - CSV file with business details
  - Ready for outreach