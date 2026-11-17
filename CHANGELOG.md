# Changelog

## 0.3.1 — 2026-11-17
- Skill: always run `in` on the answer before triage; don't put the command into a shell variable. Same inside-a-journal rule as animus-journal.

## 0.3.0 — 2026-11-17
- New `drop <id>`: removes a broken or mistaken request and its answers.
- `save` refuses a body without an `Answer format` section (a cut-off heredoc); `--force` overrides.
- `in` no longer crashes when a request file is missing. Skill: long requests go through a file.

## 0.2.0 — 2026-11-17
- `in -` takes an answer pasted into the chat from stdin; a second round for an answered request works and keeps the earlier answer.
- `in`/`close --id` accept a unique id prefix; unknown ids list the known ones; a missing answer file shows its full path and nearby .md files.
- Review ids are cut at a word boundary. Skill: Windows interpreter from ecosystem.json.

## 0.1.1 — 2026-11-17
- Skill: never cat/edit request or answer files — `in` prints both; to change a request, save a new one and close the old.
- `sizes` says the token total is files to read, separate from the reviewer's reasoning budget.

## 0.1.0 — 2026-11-17
- First release, part of the Animus ecosystem.
