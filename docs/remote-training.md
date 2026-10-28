# Free remote GPU training: Kaggle-first plan

This guide targets users whose Windows PC does not have a suitable GPU and whose budget is **₹0 / $0**. The preferred option to investigate is Kaggle Notebooks' free GPU tier. This is not yet a one-click remote trainer, and free GPU access is limited rather than guaranteed.

## Free-only policy for this project

- Do not use paid GPU providers or paid APIs.
- Do not enter payment details or enable billable cloud services for this workflow.
- If Kaggle does not offer a GPU session, stop and wait for availability or a quota reset; do not switch to a paid provider.
- Review Kaggle's current rules and notebook settings before uploading voice recordings or running training code.

## Candidate: Kaggle Notebooks (free GPU)

Official links:

- [Kaggle Notebooks documentation](https://www.kaggle.com/docs/notebooks)
- [Kaggle efficient GPU usage guide](https://www.kaggle.com/docs/efficient-gpu-usage)
- [Kaggle Terms of Use](https://www.kaggle.com/terms)

Kaggle's documentation describes free NVIDIA GPU access, commonly with a weekly quota (the published guide says up to 30 hours per week, subject to availability and current limits). GPU sessions can be queued, and session/runtime limits apply. Check the live account UI because quotas and hardware availability can change.

### Manual preparation steps

1. Create or sign in to your Kaggle account and open a new Notebook.
2. In **Settings → Accelerator**, select an available GPU. If no free GPU is available, do not use a paid alternative.
3. Confirm that Internet access and the notebook's intended workload are allowed under Kaggle's current terms.
4. Prepare recordings locally in OneClick-AI-Cover. Use only your own voice or recordings you have explicit permission to use.
5. Before uploading any audio, check the Dataset privacy settings and make it private. Do not publish voice recordings, checkpoints, or model files.
6. Train only after the notebook's RVC setup and training steps have been reviewed and tested. Save checkpoints to the notebook's persistent output area and download the final inference-ready `.pth` model before the session expires.
7. Stop the GPU session when finished to preserve the free quota.

**Important:** these are setup and privacy instructions, not a claim that RVC training already works in Kaggle. The project's pinned RVC backend uses a WebUI and has dependencies/model assets that still need a compatible, tested notebook workflow. Do not expose a public Gradio/tunnel URL for private voice data.

## Why this project does not default to Google Colab

Google's official Colab FAQ says free resources are not guaranteed and fluctuate. It also states restrictions on deepfake activity in managed runtimes and warns about some web-UI-based content-generation workflows. Because the rules may apply to some voice-conversion workflows, this project does not rely on Colab as its default.

- [Google Colab official FAQ and resource limits](https://research.google.com/colaboratory/faq.html)

## Privacy and rights checklist

- Use only your own voice or recordings you have explicit permission to use.
- Keep voice datasets and checkpoints private; never commit them to this public GitHub repository.
- Review Kaggle's current privacy, retention, and acceptable-use terms before uploading audio.
- Treat voice recordings and trained voice models as sensitive personal data.
- Use songs and other audio only when you have the rights or permission required for your intended use.

## Current project limitations

- OneClick-AI-Cover prepares recordings locally and can launch the pinned RVC training UI locally.
- A tested Kaggle notebook, remote training orchestration, automatic checkpoint syncing, and remote model download/import are **not implemented yet**.
- Training has not been verified end-to-end on a physical Windows PC or a cloud GPU.
- The project will not promise that a free GPU is always available; it will not require a paid provider as a fallback.
