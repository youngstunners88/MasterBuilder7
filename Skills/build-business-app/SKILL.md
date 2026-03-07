---
name: build-business-app
description: |
  Build a business/productivity tool or game.
  
  Use when:
  - User wants business planning tools
  - User wants idea generation apps
  - User wants entrepreneur games
  - User shares business workbook/PDF
  
  Don't use when:
  - User wants English learning (use build-english-game)
  - User wants DIAMONDS game (use build-diamonds-game)

inputs:
  app_type: canvas|generator|simulator|workbook
  features: templates|export|ai_suggestions|collaboration

tools:
  - update_space_route
  - read_file (for workbook content)
  - read_webpage (for research)

output: Business tool at https://youngstunners.zo.space/<app>

examples:
  - "Add business model canvas" → Canvas tool
  - "Build idea generator" → SCAMPER/Brainstorm tool
  
negative_examples:
  - "Add spelling game" → use build-english-game
  - "Make diamond miner" → use build-diamonds-game