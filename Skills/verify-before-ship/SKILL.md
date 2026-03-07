---
name: verify-before-ship
description: Verify output before sending/delivering - follow the "No Laziness" principle
metadata:
  author: youngstunners.zo.computer

## Verification Checklist
Before any output/message:
- [ ] Is the content correct?
- [ ] Does it follow the user's request?
- [ ] Are there typos or errors?
- [ ] Is the tone appropriate?
- [ ] Did I test the code/feature?

## For zo.space Routes
Before marking complete:
- [ ] Route builds without errors (check get_space_errors)
- [ ] Page loads correctly (check via curl)
- [ ] All features implemented

## For Skills
- [ ] SKILL.md complete with frontmatter
- [ ] scripts/ directory has executables
- [ ] Works when run

## For Messages
- [ ] Answer is direct, not filler
- [ ] Links work (full URLs for Telegram)
- [ ] Attachments included if needed