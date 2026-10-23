# Agent Instructions

- Follow applicable parent instructions and the current user request.
- Read relevant files and follow existing team conventions before editing.
- Stay within the current task; preserve unrelated work.
- Do not invent requirements, architecture, technologies, or product decisions.
- Use the simplest solution that satisfies approved requirements.
- Add dependencies only when technically necessary.
- Avoid unnecessary abstractions, classes, wrappers, and infrastructure.
- Do not rewrite working code without a concrete reason.
- Before major changes, propose a short plan.
- Find the root cause of an error before fixing it.
- Run the minimum relevant checks after changes: tests, build, or lint as applicable.
- Never claim something works unless verified; report skipped checks and why.
- Keep file reads and log output focused; avoid dumping large files or logs.
- Keep responses concise: changes made, checks run, and remaining problems.
- Do not perform destructive operations or modify secrets without permission.
- Never expose or commit secrets.
- Do not commit or push changes unless explicitly requested.
- Create additional documentation only when necessary.

## Documentation and Spec Kit

- AGENTS.md defines agent behavior; README.md describes the project and its setup.
- Let Spec Kit create specifications, plans, and tasks; do not create substitutes.
- Avoid duplicating content across instructions, README, and Spec Kit artifacts.
- When `.specify/memory/constitution.md` exists, read it and follow the agreed project principles.
- Until the team agrees on scope and implementation, do not start application development.
