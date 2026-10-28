# Community and contribution guide

OneClick-AI-Cover is a free, open-source project. Community contributions should make the workflow safer, clearer, and more reliable for people using modest Windows PCs.

## Best ways to help

- Reproduce setup failures and share the exact error text, Windows version, RAM, CPU, and whether an NVIDIA GPU is available.
- Improve the beginner workflow, accessibility, documentation, and plain-language error messages.
- Add tests for audio preparation, conversion argument handling, file validation, and export.
- Test on different Windows configurations and report what actually worked; do not claim success from a static check alone.
- Help maintain a compatibility matrix for RVC backend versions, Python versions, model assets, and supported model formats.
- Review third-party licenses and document model/download requirements.

## Issue template checklist

When opening an issue, include as much as is safe to share:

- What you tried and the exact steps to reproduce it.
- What you expected and what happened instead.
- Windows version, CPU, RAM, GPU, and free disk space.
- The relevant error message with personal paths, usernames, tokens, and private data removed.
- Whether the problem occurs during setup, recording preparation, vocal separation, voice conversion, or export.

Do not upload songs, voice recordings, voice models, checkpoints, logs containing private paths, or credentials to a public issue.

## Contribution principles

- Keep the app local-first and free to use; do not add paid API requirements, telemetry, or hidden cloud uploads.
- Do not make a paid service the only way to complete the core workflow.
- Keep tests small, reproducible, and offline where possible.
- Describe hardware limits and incomplete integration honestly.
- Use only voices, audio, and test assets you have rights or permission to use.
- Document third-party licenses; the project's MIT license covers original project code only.

See CONTRIBUTING.md for the existing contribution rules and ETHICS_AND_LEGAL.md for legal and ethical boundaries.
