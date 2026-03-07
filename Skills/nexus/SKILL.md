---
name: nexus
description: Unified autonomous production system for English learning games + DIAMONDS crypto apps
metadata:
  author: youngstunners.zo.computer
---

## When to use this skill
- Build English learning games (vocab, grammar, reading, spelling games)
- Build DIAMONDS protocol apps (miner game, quiz, oracle)
- Create educational web apps with React
- Deploy to zo.space
- Coordinate the two divisions (English Academy + DIAMONDS Games)

## When NOT to use this skill
- For simple file edits (use edit_file_llm)
- For web searches (use web_search)
- For installing packages (use pip/npm directly)
- For checking system stats (use list_files, get_space_errors)

## Inputs
- `app_type`: english-game, diamonds-game, business-tool
- `game_name`: Specific game to build
- `feature`: Feature to add

## Outputs
- React apps deployed to zo.space
- New routes created
- Games with levels, achievements, leaderboards

## Usage
```bash
# This skill works through direct tool calls:
# 1. update_space_route - create new games/apps
# 2. list_space_routes - see all deployed apps
# 3. get_space_errors - debug issues
```

## Architecture
- **ENGLISH ACADEMY** (Division 1): Learning games at /english/*
- **DIAMONDS GAMES** (Division 2): Crypto games at /diamonds-*
- **BUSINESS FORGE** (Division 3): Innovation tools at /business-*

## Negative examples
- Don't use for: reading local files (use read_file)
- Don't use for: running local scripts (use run_bash_command)
- Don't use for: searching the web (use web_search)
- Don't use for: sending emails (use send_email_to_user)