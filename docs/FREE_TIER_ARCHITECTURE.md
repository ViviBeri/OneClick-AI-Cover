# Free-tier and local-first model strategy

## Non-negotiable project constraints

OneClick-AI-Cover is intended to remain usable without subscriptions, paid API keys, metered inference endpoints, or required cloud compute.

- Audio separation, voice conversion, mixing, and export run locally on the user's computer.
- PyTorch is an inference/runtime dependency, not a hosted service.
- Hugging Face Hub may be used only as an optional public-model discovery and download source.
- Do not require a Hugging Face access token for public repositories or public files.
- Do not call paid inference APIs, hosted Spaces, paid GPU services, or metered endpoints from the app.
- Do not upload songs, voice recordings, datasets, generated audio, or private model files automatically.
- Manual import of a compatible local RVC .pth model must remain available if Hugging Face is unavailable.
- Users are responsible for checking the model card, license, voice consent, and redistribution terms before using a model.

## Free Hugging Face usage

The free approach is limited to public Hub metadata and public file downloads subject to Hugging Face's current free-tier limits, rate limits, bandwidth policies, and repository terms. Free access is not an unlimited bandwidth or storage guarantee.

Do not add paid inference, private/gated model access, or token prompts as a requirement. If a public model requires authentication or acceptance of gated terms, mark it unavailable for anonymous download and keep manual import as the alternative.

## Safe model handling

RVC .pth files can contain pickle-based data. Treat downloaded model files as untrusted. Do not automatically load arbitrary weights merely to inspect them, and do not execute code from model repositories. Before adding automated downloads:

1. Require an explicit user action and show the repository, exact filename, size, and license/model-card link.
2. Restrict downloads to public files from the Hugging Face Hub.
3. Download to a temporary file, verify HTTP completion and expected size/hash when the publisher provides one, then move it into the local model folder.
4. Keep the manual .pth import path.
5. Validate compatibility with the pinned RVC backend without claiming that file extension alone proves compatibility.

## Current implementation boundary

The current app uses local Demucs and a pinned local RVC backend. Its model import flow accepts a local .pth file. A Hugging Face browser/downloader is a future optional enhancement, not a reason to replace the working RVC inference adapter or require a Hub account.

The project must continue to work with the current manual model import workflow when Hugging Face integration is disabled or unavailable.
