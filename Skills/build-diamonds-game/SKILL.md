---
name: build-diamonds-game
description: |
  Build a DIAMONDS protocol themed game or app.
  
  Use when:
  - User wants game about $DIAMONDS token
  - User mentions lilbunt character
  - User mentions @richland100 or Blaze3Win
  - User wants crypto/staking themed game
  
  Don't use when:
  - User wants English learning game (use build-english-game)
  - User wants business tool (use build-business-app)

inputs:
  game_type: mining|trading|staking|prediction|quiz
  features: wallet_connect|leaderboard|achievements|story_mode

tools:
  - update_space_route (create at /diamonds-* or /english/diamonds-*)
  - list_space_routes (check existing DIAMONDS games)

output: Working DIAMONDS game at https://youngstunners.zo.space/diamonds-<game>

examples:
  - "Add diamond mining game" → lilbunt miner game
  - "Make prediction game for DIAMONDS" → oracle prediction
  
negative_examples:
  - "Add vocabulary game" → use build-english-game
  - "Build business forge" → use build-business-app