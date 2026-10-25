# Security and privacy

- Do not commit private avatars, reference screenshots, source videos, exported conversations, credentials, or run outputs.
- Use absolute local paths for private assets. They are read only during rendering and are not copied into this repository.
- Check `git status --ignored` and run `python3 release_audit.py` before every public push.
- Report potential disclosure issues privately to the repository owner; do not include private files in a public issue.
