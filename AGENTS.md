# Agent Instructions

This repository is worked on by more than one AI coding agent (Codex, Claude
Code, and possibly others) across different sessions. Conversation history
does not carry over between them — this file, the `.ai/` directory, and git
are the persistent source of truth. Do not assume you are the only agent
that has touched this repo.

## Session start

Before doing substantial work:
1. Read `.ai/PROJECT.md`, `.ai/STATE.md`, `.ai/NEXT.md`, `.ai/DECISIONS.md`,
   `.ai/KNOWN_ISSUES.md`.
2. Run `git status`, `git log --oneline -10`, and check for uncommitted diffs.
3. If `.ai/` disagrees with actual code or git state, **trust the code and
   git — not the `.ai/` prose** — and correct the stale file.

`NOTLAR.md` (Turkish) is the human-maintained, detailed decision log and
interview-prep narrative for this project. `.ai/DECISIONS.md` is a distilled
version of it for agents — read `NOTLAR.md` if you need the full reasoning
behind a specific choice.

## During work

- Update `.ai/STATE.md` when implementation status materially changes.
- Update `.ai/NEXT.md` when priorities or unfinished work change.
- Update `.ai/DECISIONS.md` only for non-obvious architectural/design
  decisions another agent would need to know later — not every small
  choice.
- Update `.ai/KNOWN_ISSUES.md` when you find or fix a real bug/limitation.
- Don't update all five files for a one-line fix. Use judgment.

## Git safety

- Never `git reset --hard`, force-push, or discard uncommitted changes you
  didn't write, without explicit confirmation.
- Don't assume existing uncommitted changes are yours to overwrite —
  inspect them first.
- Prefer new commits over amending existing ones.

## Project specifics

See `.ai/PROJECT.md` for stack, architecture, and run/test commands. Short
version: Python 3.14, FastAPI + a rule-based RAG + MCP server, all built on
top of one shared `src/turbinetwin/` package — don't duplicate logic between
the API layer and the MCP layer.
