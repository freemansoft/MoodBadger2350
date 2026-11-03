# MoodBadger2350

## Claude Code plugins

This project requires the plugins below. They are declared in `.claude/settings.json`, and a `SessionStart` hook there installs any that are missing, at project scope. To install them by hand:

```sh
claude plugin install superpowers@claude-plugins-official --scope project
claude plugin install skill-creator@claude-plugins-official --scope project
```

| Plugin          | Marketplace                          | Use it for                                                                       |
| --------------- | ------------------------------------ | -------------------------------------------------------------------------------- |
| `superpowers`   | `anthropics/claude-plugins-official` | Brainstorming, plans, TDD, systematic debugging, code review, verification       |
| `skill-creator` | `anthropics/claude-plugins-official` | Creating and improving skills, running skill evals, tuning skill descriptions    |

Plugin skills are namespaced: invoke `superpowers:brainstorming`, not `brainstorming`.

### Superpowers

Check for a relevant superpowers skill before starting work, and use it when one applies:

- New features or behavior changes: `superpowers:brainstorming`, then `superpowers:writing-plans`
- Carrying out a plan: `superpowers:executing-plans` or `superpowers:subagent-driven-development`
- Writing code: `superpowers:test-driven-development`
- Bugs and unexpected behavior: `superpowers:systematic-debugging`
- Before claiming work is done: `superpowers:verification-before-completion`
- Reviews: `superpowers:requesting-code-review`, `superpowers:receiving-code-review`
- Wrapping up: `superpowers:finishing-a-development-branch`

### Skill creator

Use `skill-creator:skill-creator` to add a project skill under `.claude/skills/`, or to improve an existing one, including measuring it with evals and tuning its description so it triggers reliably.
