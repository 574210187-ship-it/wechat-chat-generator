# Agent operating contract

1. Treat this as a local layout renderer, not a messaging client or evidence generator.
2. Start from `examples/project.json` or a user-provided project. Never guess a person’s identity, avatar, or real conversation from a reference image.
3. Keep every user avatar, screenshot, video, and source asset outside git. `runs/` is intentionally ignored.
4. Use `REVIEW` by default. `AUTO` is allowed only when the user explicitly asks for automatic execution.
5. Read `state.json` before resuming. Repair only the current stage; do not mark later gates passed after an error.
6. Use `--replace FROM=TO` only for explicit user-directed text replacement and preserve it in `normalized-project.json`.
7. Before delivery, verify `state.json.status == "COMPLETED"`, the requested outputs exist and are non-empty, and the requested theme/title/participants match the project.
8. Describe outputs as generated WeChat-style layouts or demonstrations. Never call them authentic chat, payment, or legal records.
