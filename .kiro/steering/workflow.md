# Development Workflow

## Feature and change workflow

Follow this sequence for every feature, fix, or change:

1. **Build** the feature or change.
2. **User tests** it (I wait for the user to try it).
3. **User confirms** it works as expected.
4. **Align all documentation before committing.** Update every doc affected by
   the change — `README.md`, `ROADMAP.md`, `CHANGELOG.md`, files under `docs/`,
   and any relevant ADRs. Docs must reflect reality before the commit is made.
5. **Provide one commit message** that covers the code and docs together.

## Rules

- Never leave docs stale. If a change alters behavior, keybindings, features,
  status, or configuration, the docs must be updated in the same commit as the
  code.
- Do not commit on the user's behalf unless explicitly asked. Provide the
  commit message and let the user commit.
- Before proposing a commit message, verify docs are aligned with the change.

## Quality gates before committing

- Run `ruff check`, `mypy src`, and the test suite. All must pass.
- Add or update tests for new features and bug fixes (do not add tests unless
  the change warrants them or the user asks).
