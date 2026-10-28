# Remote GPU training: safe next steps

This guide is for training a model from your own voice recordings when your Windows PC does not have a suitable GPU. It is a planning guide, not a one-click remote trainer.

## Recommended approach

1. Prepare and review your recordings locally using OneClick-AI-Cover. Keep the originals and prepared dataset private.
2. Choose a remote compute provider whose current terms explicitly allow your intended voice-conversion training workload.
3. Check the provider's current price, included credits, identity/payment requirements, data retention policy, and GPU availability before uploading audio.
4. Upload only the recordings needed for training. Do not upload recordings of other people unless you have their informed permission.
5. Save model checkpoints and the final inference-ready model to storage you control. Download the final model and import it into OneClick-AI-Cover.

## Candidate to investigate: Modal

Modal's official pricing page currently lists a Starter plan at $0/month plus usage, with $30/month in compute credits. It also lists GPU rates separately; for example, the T4 GPU line is $0.000164/second (about $0.59/hour for GPU time alone). CPU, memory, storage, and other usage may add costs, and usage above included credits can be billed. Review the live price and account billing settings before launching any job:

- [Modal official pricing](https://modal.com/pricing)
- [Modal official website](https://modal.com/)

**Do not assume this will be completely free or that the credits will cover a full training run.** Estimate the workload, confirm that credits are available on your account, and set any available spending/budget controls before running code. This project has not yet been tested on Modal, and no Modal training script is included.

## Why this guide does not recommend relying on free Google Colab

Google's official Colab FAQ says free resources are not guaranteed and fluctuate. It also explicitly prohibits deepfake activity in managed runtimes and says free sessions may be terminated for workflows that bypass notebook interaction to use a web UI for content generation. Because those restrictions may apply to some voice-conversion workflows, review the current terms carefully rather than relying on an RVC WebUI notebook to stay available.

- [Google Colab official FAQ and resource limits](https://research.google.com/colaboratory/faq.html)

## Before uploading recordings

- Use only your own voice or recordings you have explicit permission to use.
- Avoid public links or public repositories for voice datasets and checkpoints.
- Read the provider's privacy, retention, and acceptable-use terms.
- Treat voice recordings and trained voice models as sensitive personal data.
- If the provider requires a public endpoint or shared app, do not expose it unless you understand the access controls and have secured it.

## Current project limitations

- OneClick-AI-Cover currently prepares recordings locally and can launch the pinned RVC training UI locally.
- Remote training orchestration, remote uploads, automatic checkpoint syncing, and remote model downloads are **not implemented**.
- Training has not been verified end-to-end on a physical Windows PC or a cloud GPU.
