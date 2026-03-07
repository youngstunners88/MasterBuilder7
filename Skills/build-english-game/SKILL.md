---
name: build-english-game
description: |
  Build a new English learning game as a zo.space page route.
  
  Use when:
  - User wants a new vocabulary/grammar game
  - User asks for "add a game" or "create game"
  - User wants to gamify English learning
  
  Don't use when:
  - User wants DIAMONDS crypto game (use build-diamonds-game)
  - User wants business tool (use build-business-app)
  - User wants to modify existing game (use update-game)

inputs:
  game_type: vocabulary|grammar|reading|typing|speed
  difficulty: beginner|intermediate|advanced
  features: multiplayer|achievements|timer|levels

tools:
  - update_space_route (create page at /english/<game>)
  - list_space_routes (check existing games)
  - get_space_errors (verify it works)

output: Working game at https://youngstunners.zo.space/english/<game>

examples:
  - "Add a spelling game" → build spelling bee with 25 words
  - "Make a typing game" → build speed typing with WPM tracking
  
negative_examples:
  - "Add DIAMONDS game" → wrong skill, use build-diamonds-game
  - "Fix the maze" → wrong skill, use update-game