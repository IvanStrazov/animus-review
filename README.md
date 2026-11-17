# animus-review

[![tests](https://github.com/IvanStrazov/animus-review/actions/workflows/test.yml/badge.svg)](https://github.com/IvanStrazov/animus-review/actions/workflows/test.yml)
[![version](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md)
[![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen)
![python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)

**A second opinion from another model — a focused package out, a triaged answer back.**

> **Part of Animus** — small, local, token-frugal plugins that let Claude Code remember you and your work. Each works alone; together they share context through `~/.claude/ecosystem.json`.
>
> | Plugin | What it does |
> |---|---|
> | [animus-journal](https://github.com/IvanStrazov/animus-journal) | Project journal on a hard token budget: what was done, decided, next |
> | [animus-portrait](https://github.com/IvanStrazov/animus-portrait) | A compact portrait of you, built from your own sessions |
> | [animus-brief](https://github.com/IvanStrazov/animus-brief) | One status brief across all your projects |
> | [animus-limits](https://github.com/IvanStrazov/animus-limits) | Token spend per task, per-task limits, cost estimates |
> | [animus-relay](https://github.com/IvanStrazov/animus-relay) | Hand work over to a fresh session without losing the thread |
> | [animus-review](https://github.com/IvanStrazov/animus-review) | Send work to another model for review, triage the answer |
>
> The name nods to the memory machine from Assassin's Creed and to the Latin *animus*, "mind". Not affiliated with Ubisoft.

## Install

```
/plugin marketplace add IvanStrazov/animus-review
/plugin install animus-review@animus-review
```

Then say `/review`. Requires Python 3.9+ on `PATH` (`python3` or `python`); works on macOS, Linux and Windows (Git Bash).

## What you get

**Out** — "prepare this for review by another model" or `/review`. Claude builds a package: the reviewer's role, short context, what was done (with numbers), **numbered questions**, what is out of scope, the files to read in order with their size in tokens, a reading budget, and a strict answer format (verdict; findings F1…Fn with severity, evidence, proposal, effort). You paste or attach it to any model: Fable, GPT, Gemini, a fresh Claude.

**Back** — "the review results are in file X". Claude pairs the answer with its request and triages every finding into **accept / reject / discuss** with reasons, disagreeing openly when the reviewer is wrong. Nothing is implemented until you confirm. The outcome goes to [animus-journal](https://github.com/IvanStrazov/animus-journal) and the accepted items to the project's next steps.

Requests and answers live in `<project>/.journal/review/` with an `INDEX.md` (open / answered / closed), git-ignored.

## Token budget

No hooks. Building a package costs the files Claude reads to write it; `sizes` tells you what the *reviewer* will read before you send it. Bringing an answer back costs the answer (printing is capped at 60 000 chars).

## Commands

```
review.py gather [--topic WORDS]
review.py sizes FILE...
review.py save --title T          # stdin -> request
review.py in ANSWER.md [--id ID]
review.py close ID [--note TEXT]
review.py list
```

## Privacy

Everything stays on your machine: plain Markdown and JSON files, no network, no database, one stdlib Python script.

## License

MIT
