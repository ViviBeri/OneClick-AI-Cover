# Free remote GPU training: Kaggle-first plan

This guide targets users whose Windows PC does not have a suitable GPU and whose budget is **₹0 / $0**. Kaggle's free GPU tier is the candidate to investigate, not a guaranteed service or a working one-click trainer.

## Free-only policy for this project

- Do not use paid GPU providers or paid APIs.
- Do not enter payment details or enable billable cloud services for this workflow.
- If Kaggle does not offer a free GPU session, stop and wait for availability or a quota reset; do not switch to a paid provider.
- Review Kaggle's current rules and notebook settings before uploading voice recordings or running training code.

## Notebook available: preflight only

Open [`notebooks/kaggle_rvc_training_preflight.ipynb`](../notebooks/kaggle_rvc_training_preflight.ipynb) in Kaggle. It checks the runtime, lists audio files attached as notebook input, and checks out the exact RVC backend revision pinned by this project. It does **not** install the complete training environment, run training, export checkpoints, or download a trained model. Those stages are intentionally not advertised as working until validated end-to-end.

Official links:

- [Kaggle Notebooks documentation](https://www.kaggle.com/docs/notebooks)
- [Kaggle efficient GPU usage guide](https://www.kaggle.com/docs/efficient-gpu-usage)
- [Kaggle Terms of Use](https://www.kaggle.com/terms)

GPU availability, quotas, session/runtime limits, and terms can change. Check the live account UI and current terms. If a free GPU is not offered, stop rather than enabling paid compute.

## Safe preparation

1. Create or sign in to your Kaggle account and open a Notebook.
2. In **Settings → Accelerator**, select an available free GPU.
3. Confirm Internet access and the intended workload are allowed by current Kaggle terms.
4. Prepare recordings locally in OneClick-AI-Cover. Use only your own voice or recordings you have explicit permission to use.
5. Attach recordings as a **private Kaggle Dataset**. Do not publish recordings, checkpoints, or models.
6. Do not expose a public Gradio/tunnel URL for private voice data.
7. Stop the GPU session when finished to preserve the free quota.

## Why this project does not default to Google Colab

Google's official Colab FAQ says free resources are not guaranteed and fluctuate. It also describes restrictions on deepfake activity in managed runtimes and cautions about some web-UI-based content-generation workflows. Because these rules may apply to some voice-conversion workflows, this project does not rely on Colab as its default.

- [Google Colab official FAQ and resource limits](https://research.google.com/colaboratory/faq.html)

## Privacy and rights checklist

- Use only your own voice or recordings you have explicit permission to use.
- Keep voice datasets and checkpoints private; never commit them to this public GitHub repository.
- Review Kaggle's current privacy, retention, and acceptable-use terms before uploading audio.
- Treat voice recordings and trained voice models as sensitive personal data.
- Use songs and other audio only when you have the rights or permission required for your intended use.

## Current project limitations

- OneClick-AI-Cover prepares recordings locally and can launch the pinned RVC training UI locally.
- The notebook is currently a **preflight scaffold**, not a tested Kaggle training pipeline.
- Remote training orchestration, automatic checkpoint syncing, and remote model download/import are not implemented.
- Training has not been verified end-to-end on a physical Windows PC or a cloud GPU.
- The project will not promise that a free GPU is always available and will not require a paid provider as a fallback.
