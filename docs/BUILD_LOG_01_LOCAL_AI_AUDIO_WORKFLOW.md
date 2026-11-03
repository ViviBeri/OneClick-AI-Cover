# Build Log 01 — Designing a Local-First AI Audio Workflow

**Project:** OneClick-AI-Cover  
**Focus:** Audio pipeline boundaries, model handling, failure detection, and honest verification  
**Status:** Early integration build

## The engineering problem

A singing-cover workflow combines tools with different runtime requirements and failure modes. Audio decoding, source separation, voice conversion, sample-rate handling, mixing, and export must work together without hiding a failed stage behind a stale output file.

The project is a Windows-first local Gradio application. Audio processing runs on the user's machine; public Hugging Face access is optional and limited to model-card discovery and downloads.

## Pipeline design

The current application coordinates these stages:

1. **Validate input.** Accept supported audio formats and reject invalid inputs before processing.
2. **Prepare audio.** Convert the selected track to a working WAV file.
3. **Separate sources.** Invoke Demucs in a subprocess to produce vocals and instrumental stems.
4. **Convert vocals.** Invoke the separately managed RVC backend with an inference-ready .pth model.
5. **Reconcile audio.** Match the converted vocal's sample rate to the instrumental, then mix both tracks with configurable gains.
6. **Export.** Produce WAV output, with optional MP3 export when FFmpeg is available.

The Gradio interface coordinates the workflow; processing modules keep separation, conversion, and audio utilities in distinct units.

## Runtime and model boundaries

The root application and the RVC backend are deliberately treated as separate Python environments. The conversion adapter checks for the backend CLI and its managed interpreter before launching inference. Installing UI dependencies does not imply that a working RVC runtime is present.

The model browser is separated from active inference models. A downloaded public .pth file is placed in an unverified holding directory rather than being made immediately selectable. A user must review the publisher, model card, license, and voice permissions before deliberately importing it into the active voice directory.

This is a security and consent boundary, not a guarantee that every downloaded model is safe or compatible.

## Failure handling

The code includes several defensive checks:

- Input audio and selected model paths are validated before processing.
- Subprocess failures preserve diagnostic output in the raised error.
- Old output files are removed before conversion or mixing, so a failed attempt cannot leave an earlier result looking current.
- RVC output is checked for existence, non-zero size, and readable audio metadata.
- Audio mixing rejects non-finite or negative gains, checks sample rates, handles mono/stereo inputs, and limits peaks.
- Model downloads are quarantined until a separate import action.

These checks improve failure visibility. They do not prove that every upstream Demucs or RVC configuration will work on every Windows machine.

## Automated verification and its limits

The repository contains unit tests for audio utilities, conversion behavior, model handling, the processing pipeline, and validation. GitHub Actions also runs tests and Windows application smoke checks.

The verification guide distinguishes CI smoke coverage from a clean-machine installation and a real-audio end-to-end conversion. A successful test suite does not establish that a fresh Windows installation, Demucs model download, compatible RVC model, GPU/CPU inference, or final audio export has been validated together.

The current project status therefore remains **early integration build**. Outstanding manual evidence includes:

- A clean Windows x64 installation report.
- A successful full conversion using audio and a voice model the tester is authorized to use.
- Recorded environment details, logs, and output checks.
- Performance measurements for memory, CPU, and GPU use.

## Dependency reproducibility work

A separate pull request, [#16](https://github.com/ViviBeri/OneClick-AI-Cover/pull/16), is working on a resolver-generated uv.lock for the root application environment. It intentionally keeps the Python 3.12 RVC backend environment separate. The PR is still open; its lockfile and validation work should not be described as merged into main.

At the time this log was written, the latest visible Tests workflow run on that PR revision completed successfully. The PR description also reports a SonarCloud Quality Gate failure for the new-code C Security Rating, which remains a review item before merge.

## Engineering takeaway

The central design decision is to make each external processing stage explicit and observable. The application should report which stage failed, verify that outputs are real files, and avoid silently promoting unreviewed model downloads into the active inference path.

The next meaningful milestone is not another visual feature. It is reproducible evidence from a clean Windows machine and a complete, consent-safe audio conversion.

---

*This log describes the repository implementation and verification records. It does not claim a successful real-audio conversion or clean-machine installation.*