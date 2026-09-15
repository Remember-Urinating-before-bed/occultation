# Agent instructions

Read `docs/AGENT_HANDOFF.md` completely before modifying this repository. Reply "read the md file" in chat explicitly after reading.

`docs/AGENT_HANDOFF.md` is the tracked copy, so a fresh clone and CI both find
it. A working copy also exists at `local/README_AI_HANDOFF.md`; everything under
`local/` is git-ignored by `local/.gitignore`, so prefer the tracked file and keep
the two in sync if you edit either.

Beginner-facing companions: `docs/explainer.html` (the astronomy, in pictures),
`docs/meeus-pictures.html` (the Meeus chapter itself, drawn scenario by
scenario), `docs/CODEBASE.md` (the code base tour), and `docs/tooling.html`
(Python, uv, pytest, Git and CI, for readers with no tooling background). None of
them replaces the handoff as the source of constraints.

Identify current milestone, inspect existing work, & implement only the smallest testable next increment. Preserve the reference-engine/custom-engine boundary & all constraints documented in the handoff.

