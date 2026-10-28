# Legal and ethical use

OneClick-AI-Cover is a local-first audio tool. Its availability does not grant permission to use a voice, recording, song, composition, or model.

## Allowed-use baseline

- Prefer your own voice and audio you created or are authorized to use.
- Get informed permission before training on or converting another person's voice. Do not treat a publicly available recording as consent.
- Do not use the tool to impersonate someone deceptively, fabricate statements, harass or defame a person, commit fraud, evade identity checks, or create non-consensual intimate or other abusive audio.
- When sharing AI-generated or voice-converted audio, label it clearly when listeners could reasonably mistake it for a real performance or statement.
- Respect copyright and any licenses covering songs, stems, recordings, datasets, RVC models, pretrained assets, and dependencies. Private/local processing does not automatically make a use lawful.
- Check the laws and platform rules that apply to your location and intended use. This project is not legal advice.

## Voice data and privacy

- Voice recordings and trained voice models can be identifying and sensitive.
- Keep datasets, source recordings, model checkpoints, API keys, and generated audio out of public Git repositories. The repository ignore rules exclude common audio and dataset paths, but check every commit before pushing.
- The app's local preparation workflow does not intentionally upload recordings. A separate remote GPU workflow would require uploading files to the provider; review the provider's current terms, privacy settings, and retention rules before doing so.
- Never expose a public notebook, Gradio share link, or tunnel containing private recordings or model files without understanding access controls.
- Delete temporary uploads and cloud copies when no longer needed, where the service permits it.

## Reporting misuse or a security issue

Please report a concern through the repository's GitHub Issues page: https://github.com/ViviBeri/OneClick-AI-Cover/issues. Do not attach private voice recordings, model weights, credentials, or personal information to an issue. For a sensitive security issue, avoid publishing exploit details until maintainers can assess the report.

## Scope

These guidelines describe project expectations; they do not replace professional legal advice or the terms of third-party tools and model weights. Maintainers may update the guidance as applicable laws, platform policies, and dependencies change.
