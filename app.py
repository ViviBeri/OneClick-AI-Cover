from __future__ import annotations
import logging, sys, tempfile, shutil
from pathlib import Path
import gradio as gr
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from oneclick_cover.audio_utils import match_sample_rate, mix_audio, probe_audio, transcode_to_wav
from oneclick_cover.settings import VOICE_DIR, OUTPUT_DIR, LOG_DIR
from oneclick_cover.validation import validate_audio_file, validate_voice_model
from oneclick_cover.separation import separate_vocals
from oneclick_cover.conversion import convert_voice
from oneclick_cover.training import launch_training_ui
from oneclick_cover.dataset import prepare_recordings
from oneclick_cover.settings import ROOT
from oneclick_cover.system_check import collect_system_info, format_system_report
UNVERIFIED_MODEL_DIR = ROOT / "models" / "unverified"
for folder in (VOICE_DIR, OUTPUT_DIR, LOG_DIR, UNVERIFIED_MODEL_DIR): folder.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_DIR / "oneclick-cover.log", level=logging.INFO)
def models(): return sorted(p.name for p in VOICE_DIR.glob("*.pth") if p.is_file())
def refresh_models():
    choices = models()
    return gr.Dropdown(choices=choices, value=(choices[0] if choices else None))
def import_voice_model(uploaded_file, trust_confirmed=False):
    if not trust_confirmed:
        raise gr.Error("Trust acknowledgement required. RVC may deserialize .pth pickle payloads and execute code; this checkbox does not sandbox the checkpoint.")
    if not uploaded_file:
        raise gr.Error("Choose a .pth voice model file first.")
    source = Path(uploaded_file)
    if source.suffix.lower() != ".pth":
        raise gr.Error("Only .pth RVC inference models are accepted.")
    safe_name = source.name.replace("/", "_").replace("\\", "_")
    destination = (VOICE_DIR / safe_name).resolve()
    if destination.parent != VOICE_DIR.resolve():
        raise gr.Error("Invalid model filename.")
    try:
        validate_voice_model(source)
        if source.resolve() != destination:
            shutil.copy2(source, destination)
        choices = models()
        return gr.Dropdown(choices=choices, value=destination.name), f"Imported {destination.name}. You can now select it under Generate Cover."
    except Exception as exc:
        logging.exception("Voice model import failed")
        raise gr.Error(str(exc)) from exc
def preflight_voice_model(uploaded_file):
    if not uploaded_file:
        raise gr.Error("Choose a .pth model file to inspect.")
    try:
        from oneclick_cover.model_preflight import inspect_rvc_checkpoint
        return inspect_rvc_checkpoint(Path(uploaded_file))
    except Exception as exc:
        logging.exception("Model preflight failed")
        raise gr.Error(str(exc)) from exc

def search_hf_models(query):
    try:
        from oneclick_cover.hf_models import search_public_rvc_models
        return search_public_rvc_models(query)
    except Exception as exc:
        logging.exception("Hugging Face model search failed")
        raise gr.Error(f"Public model search failed: {exc}") from exc

def download_hf_model(repo_id, filename, confirmed):
    try:
        from oneclick_cover.hf_models import download_public_pth_model
        message = download_public_pth_model(repo_id, filename, UNVERIFIED_MODEL_DIR, confirmed)
        return gr.skip(), message + "\n\nSecurity hold: this download is stored outside the active voice-model folder. It will not appear in Generate Cover. Review the file and model-card terms, then use Import Voice Model for a separate, deliberate import action only if you trust the publisher and file."
    except Exception as exc:
        logging.exception("Hugging Face model download failed")
        raise gr.Error(str(exc)) from exc

def run_system_check():
    return format_system_report(collect_system_info())

def prepare_training_dataset(uploaded_files, dataset_name, progress=gr.Progress()):
    try:
        progress(0.1, desc="Checking recordings")
        folder, count = prepare_recordings(uploaded_files or [], dataset_name, ROOT / "datasets")
        progress(1.0, desc="Recordings prepared")
        return str(folder), f"Prepared {count} recording(s). In the RVC training UI, use this folder path as the dataset/training folder. Review the upstream RVC preprocessing instructions before starting training."
    except Exception as exc:
        logging.exception("Dataset preparation failed")
        raise gr.Error(str(exc)) from exc

def generate(song, model, pitch, vocal_gain, instrumental_gain, fmt, demucs_device="cpu", demucs_segment=5.0, demucs_timeout=1800, trust_confirmed=False, progress=gr.Progress()):
    if not song: raise gr.Error("Choose an input song first.")
    if not model: raise gr.Error("Add an authorized .pth model to models/voices, then refresh.")
    if not trust_confirmed:
        raise gr.Error("Trust acknowledgement required. RVC may deserialize .pth pickle payloads and execute code; this checkbox does not sandbox the checkpoint.")
    job = None
    try:
        source=Path(song); validate_audio_file(source); model_path=(VOICE_DIR/model).resolve()
        if model_path.parent != VOICE_DIR.resolve(): raise ValueError("Invalid voice-model selection.")
        validate_voice_model(model_path)
        job=Path(tempfile.mkdtemp(prefix="cover_",dir=OUTPUT_DIR)); wav=job/"input.wav"
        progress(0.1,desc="Preparing audio"); transcode_to_wav(source,wav)
        progress(0.25,desc="Separating vocals")
        def update_separation_progress(fraction, message):
            progress(0.25 + 0.35 * fraction, desc=message or "Separating vocals")
        vocals,instrumental=separate_vocals(wav,job,progress=update_separation_progress,device=demucs_device,segment=float(demucs_segment),timeout=float(demucs_timeout))
        progress(0.6,desc="Converting voice"); converted=job/"converted.wav"; convert_voice(vocals,converted,model_path,int(pitch))
        progress(0.85,desc="Mixing"); output=job/"cover.wav"
        converted=match_sample_rate(converted,instrumental,job/"converted_matched.wav")
        mix_audio(converted,instrumental,output,float(vocal_gain),float(instrumental_gain))
        if fmt=="MP3":
            from oneclick_cover.audio_utils import export_mp3
            mp3=job/"cover.mp3"; export_mp3(output,mp3); output=mp3
        progress(1,desc="Done"); return str(output), "Saved: "+str(output)
    except Exception as e:
        if job is not None:
            shutil.rmtree(job, ignore_errors=True)
        logging.exception("Cover generation failed"); raise gr.Error(str(e)) from e
APP_CSS = """
:root {
    color-scheme: dark;
    --studio-bg: #080d18;
    --studio-panel: #111a2b;
    --studio-panel-raised: #172338;
    --studio-border: rgba(148, 163, 184, 0.16);
    --studio-text: #edf2ff;
    --studio-muted: #9aa9c2;
    --studio-accent: #8b7cff;
    --studio-accent-strong: #a99cff;
}
.gradio-container {
    width: min(100%, 1180px) !important;
    margin-inline: auto !important;
    padding: 1.25rem clamp(0.75rem, 3vw, 2rem) 3rem !important;
    background:
        radial-gradient(ellipse at 12% 0%, rgba(93, 76, 190, 0.17), transparent 34rem),
        radial-gradient(ellipse at 92% 8%, rgba(34, 160, 181, 0.10), transparent 28rem),
        var(--studio-bg) !important;
    color: var(--studio-text) !important;
}
#oneclick-studio .studio-hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    padding: clamp(1.35rem, 4vw, 2.4rem);
    margin: 0 0 1.1rem;
    border: 1px solid var(--studio-border);
    border-radius: 24px;
    background: linear-gradient(135deg, rgba(25, 36, 59, .98), rgba(15, 24, 41, .96));
    box-shadow: 0 22px 70px rgba(0, 0, 0, .22);
}
#oneclick-studio .studio-kicker {
    margin: 0 0 .7rem;
    color: #aaa0ff;
    font-size: .72rem;
    font-weight: 750;
    letter-spacing: .16em;
    text-transform: uppercase;
}
#oneclick-studio .studio-hero h1 {
    margin: 0;
    color: #f7f8ff;
    font-size: clamp(2rem, 5vw, 3.3rem);
    font-weight: 760;
    letter-spacing: -.055em;
    line-height: 1.02;
}
#oneclick-studio .studio-hero p {
    max-width: 42rem;
    margin: .8rem 0 0;
    color: #aebbd1;
    font-size: 1rem;
    line-height: 1.65;
}
#oneclick-studio .studio-local-pill {
    flex: 0 0 auto;
    padding: .65rem .9rem;
    border: 1px solid rgba(74, 222, 128, .25);
    border-radius: 999px;
    background: rgba(22, 101, 52, .18);
    color: #86efac;
    font-size: .72rem;
    font-weight: 750;
    letter-spacing: .08em;
    white-space: nowrap;
}
#oneclick-studio .studio-steps {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .75rem;
    margin: 0 0 1.25rem;
}
#oneclick-studio .studio-step {
    min-width: 0;
    padding: .9rem 1rem;
    border: 1px solid var(--studio-border);
    border-radius: 15px;
    background: rgba(17, 26, 43, .82);
}
#oneclick-studio .studio-step b {
    display: block;
    margin-bottom: .25rem;
    color: #f0edff;
    font-size: .88rem;
}
#oneclick-studio .studio-step span {
    color: var(--studio-muted);
    font-size: .76rem;
}
#oneclick-studio .tabs,
#oneclick-studio .tabitem,
#oneclick-studio .block,
#oneclick-studio .form {
    border-color: var(--studio-border) !important;
}
#oneclick-studio .tab-nav {
    gap: .35rem;
    padding: .45rem;
    border: 1px solid var(--studio-border);
    border-radius: 16px;
    background: rgba(17, 26, 43, .88);
}
#oneclick-studio .tab-nav button {
    min-height: 2.8rem;
    border-radius: 11px !important;
    color: #aab8ce !important;
    font-weight: 650;
}
#oneclick-studio .tab-nav button.selected {
    background: linear-gradient(135deg, #7668e8, #6555cf) !important;
    color: white !important;
    box-shadow: 0 5px 18px rgba(118, 104, 232, .22);
}
#oneclick-studio button.primary {
    min-height: 3.1rem;
    border: 1px solid rgba(190, 180, 255, .3) !important;
    border-radius: 12px !important;
    background: linear-gradient(135deg, #8878ff, #6859db) !important;
    color: #fff !important;
    font-weight: 750 !important;
    box-shadow: 0 8px 22px rgba(104, 89, 219, .2);
}
#oneclick-studio input,
#oneclick-studio textarea,
#oneclick-studio select {
    min-height: 2.75rem;
    border-color: var(--studio-border) !important;
    border-radius: 10px !important;
}
#oneclick-studio audio { width: 100%; }
#oneclick-studio h2,
#oneclick-studio h3 { color: #eef2ff; letter-spacing: -.02em; }
#oneclick-studio label,
#oneclick-studio .wrap { color: #d8e1f1; }
#oneclick-studio .studio-guide {
    margin: 0 0 1rem;
    padding: 1rem 1.15rem;
    border: 1px solid var(--studio-border);
    border-radius: 15px;
    background: rgba(17, 26, 43, .68);
    color: #aebbd1;
    line-height: 1.65;
}
@media (max-width: 700px) {
    .gradio-container { padding: .75rem .65rem 2rem !important; }
    #oneclick-studio .studio-hero { align-items: flex-start; flex-direction: column; border-radius: 18px; }
    #oneclick-studio .studio-local-pill { align-self: flex-start; }
    #oneclick-studio .studio-steps { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .55rem; }
    #oneclick-studio .studio-step { padding: .75rem; }
    #oneclick-studio .row,
    #oneclick-studio .gradio-row { flex-direction: column !important; align-items: stretch !important; gap: .75rem !important; }
    #oneclick-studio .column,
    #oneclick-studio .gradio-column { min-width: 0 !important; width: 100% !important; }
    #oneclick-studio button { min-height: 2.8rem; }
    #oneclick-studio input,
    #oneclick-studio textarea,
    #oneclick-studio select { font-size: 16px !important; }
    #oneclick-studio .tab-nav {
        overflow-x: auto !important;
        flex-wrap: nowrap !important;
        scrollbar-width: thin;
        -webkit-overflow-scrolling: touch;
    }
    #oneclick-studio .tab-nav button { width: auto; min-width: max-content; white-space: nowrap; }
}
@media (prefers-reduced-motion: reduce) {
    #oneclick-studio *, #oneclick-studio *::before, #oneclick-studio *::after {
        scroll-behavior: auto !important;
        animation-duration: .01ms !important;
        transition-duration: .01ms !important;
    }
}
"""

with gr.Blocks(title="OneClick AI Cover — Studio", elem_id="oneclick-studio", theme=gr.themes.Soft(primary_hue="violet", secondary_hue="cyan", neutral_hue="slate")) as demo:
    gr.HTML("""
    <section class="studio-hero">
      <div>
        <div class="studio-kicker">OneClick Audio Lab</div>
        <h1>Make your voice<br>the main event.</h1>
        <p>Create AI singing covers with local vocal separation, voice conversion and studio-style mixing. Your audio stays on your computer by default.</p>
      </div>
      <div class="studio-local-pill">LOCAL PROCESSING</div>
    </section>
    <section class="studio-steps" aria-label="Cover creation workflow">
      <div class="studio-step"><b>01 · Upload</b><span>Choose your song</span></div>
      <div class="studio-step"><b>02 · Select</b><span>Pick a trusted voice</span></div>
      <div class="studio-step"><b>03 · Create</b><span>Separate, convert, mix</span></div>
      <div class="studio-step"><b>04 · Export</b><span>Save WAV or MP3</span></div>
    </section>
    """)
    gr.Markdown("""<div class="studio-guide">**Quick start:** Import an authorized RVC <code>.pth</code> model in <strong>Import Voice Model</strong>, return to <strong>Generate Cover</strong>, choose your song and voice, then create your cover. Use only voices and audio you have permission to use. Review the <a href="https://github.com/ViviBeri/OneClick-AI-Cover/blob/main/docs/ETHICS_AND_LEGAL.md">legal and ethical use guide</a> and <a href="https://github.com/ViviBeri/OneClick-AI-Cover/blob/main/docs/COMMUNITY.md">community guide</a>.</div>""")
    with gr.Tabs():
        with gr.Tab("Generate Cover"):
            with gr.Row():
                song=gr.File(label="Song (MP3/WAV/FLAC)",file_types=[".mp3",".wav",".flac"],type="filepath")
                model=gr.Dropdown(label="RVC voice model (.pth)",choices=models())
            trust_generate=gr.Checkbox(label="I trust this .pth checkpoint and its publisher. I understand RVC may deserialize pickle data and execute code; this acknowledgement does not sandbox the file.",value=False)
            model.change(fn=lambda: False, inputs=[], outputs=trust_generate)
            refresh=gr.Button("Refresh models")
            refresh.click(refresh_models, inputs=[], outputs=model)
            pitch=gr.Slider(-12,12,value=0,step=1,label="Pitch shift")
            vocal_gain=gr.Slider(0.2,2,value=1,step=0.05,label="Vocal gain")
            instrumental_gain=gr.Slider(0.2,2,value=0.85,step=0.05,label="Instrumental gain")
            fmt=gr.Radio(["WAV","MP3"],value="WAV",label="Export format")
            with gr.Accordion("Demucs performance settings", open=False):
                demucs_device=gr.Dropdown(["cpu","auto","cuda"],value="cpu",label="Processing device",info="CPU is the safest default for low-memory PCs. CUDA requires a compatible NVIDIA GPU.")
                demucs_segment=gr.Slider(2,7,value=5,step=1,label="Segment size (seconds)",info="Smaller segments reduce peak memory use but may run slower.")
                demucs_timeout=gr.Slider(60,7200,value=1800,step=60,label="Separation timeout (seconds)",info="Stop a separation that exceeds this limit.")
            go=gr.Button("Generate cover",variant="primary")
            audio=gr.Audio(type="filepath",label="Finished cover")
            status=gr.Textbox(label="Status")
            go.click(generate,inputs=[song,model,pitch,vocal_gain,instrumental_gain,fmt,demucs_device,demucs_segment,demucs_timeout,trust_generate],outputs=[audio,status])
        with gr.Tab("Prepare Voice Recordings"):
            gr.Markdown("""## Prepare your own voice recordings
Upload recordings of your own voice, or recordings you have explicit permission to use. The app converts each file to mono WAV and stores it in a local dataset folder. Recordings are not uploaded to a cloud service by this step.

- Use clean recordings with one speaker.
- Avoid background music, reverb, clipping, and other speakers.
- This step prepares files only; it does not start training automatically.
- The installer includes a managed FFmpeg package for conversion.
""")
            dataset_name=gr.Textbox(label="Dataset folder name",value="MyVoice")
            recording_files=gr.File(label="Recordings (select multiple)",file_count="multiple",file_types=[".wav",".mp3",".flac",".m4a",".ogg",".aac"],type="filepath")
            prepare_button=gr.Button("Prepare recordings",variant="primary")
            dataset_path=gr.Textbox(label="Prepared dataset path (copy into RVC training UI)",interactive=False)
            dataset_status=gr.Textbox(label="Preparation status",interactive=False)
            prepare_button.click(fn=prepare_training_dataset,inputs=[recording_files,dataset_name],outputs=[dataset_path,dataset_status])
        with gr.Tab("System Check"):
            system_report=gr.Markdown(run_system_check())
            gr.Button("Re-check").click(fn=run_system_check,inputs=[],outputs=[system_report])
        with gr.Tab("Train My Voice (Experimental)"):
            gr.Markdown("""## Train a voice model from your own recordings

This opens the upstream RVC training interface locally. It is an advanced workflow, not yet a one-click trainer.

1. Prepare clean recordings in the previous tab.
2. Click **Open RVC Training UI** and follow the dataset, preprocessing, feature extraction, training, and index steps.
3. In the RVC interface, use the dataset path returned by the preparation tab.
4. Export the inference-ready model, then import it in the next tab.

**Hardware warning:** Training is much more demanding than inference. A low-end CPU-only PC may take many hours or days and can run out of memory. An NVIDIA GPU is strongly recommended. Train only on voices you have permission to use.
""")
            launch_train=gr.Button("Open RVC Training UI",variant="primary")
            train_status=gr.Textbox(label="Training UI status",interactive=False)
            launch_train.click(fn=launch_training_ui,inputs=[],outputs=[train_status])
        with gr.Tab("Model Preflight"):
            gr.Markdown("""## Static RVC checkpoint preflight

Select a local .pth file to inspect its PyTorch ZIP metadata without calling pickle.load() or torch.load(). The scan reports common RVC marker strings only; it cannot verify tensor shapes, actual compatibility, audio quality, or file safety. Legacy checkpoint formats may be inconclusive.

**Important:** the RVC inference backend may deserialize .pth files with torch.load(). Only import and use models from publishers you personally trust. This preflight does not make an untrusted model safe.
""")
            preflight_file=gr.File(label="RVC model (.pth)",file_types=[".pth"],type="filepath")
            preflight_button=gr.Button("Inspect checkpoint metadata")
            preflight_result=gr.Textbox(label="Static preflight report",lines=12,interactive=False)
            preflight_button.click(fn=preflight_voice_model,inputs=[preflight_file],outputs=[preflight_result])
        with gr.Tab("Free Model Browser"):
            gr.Markdown("""## Public Hugging Face model browser

Search public model-card metadata without an account or API token. Search results are community uploads, not endorsements. Review the model card, license, voice consent, and compatibility before downloading.

**Safety:** RVC .pth files may contain pickle-based data. Download only from sources you trust. The app does not inspect or load the weights during download. Downloads are quarantined in `models/unverified/` and are not selectable for conversion until you separately import them. Importing and using a `.pth` file can invoke unsafe pickle deserialization in the RVC backend; only proceed with files from publishers you trust. No song or voice recording is uploaded.
""")
            hf_query=gr.Textbox(label="Search public models",placeholder="RVC voice model")
            hf_search=gr.Button("Search public Hugging Face models")
            hf_results=gr.Textbox(label="Search results and model-card links",lines=12,interactive=False)
            hf_repo=gr.Textbox(label="Exact repository ID",placeholder="owner/repository")
            hf_filename=gr.Textbox(label="Exact .pth filename in repository",placeholder="model.pth")
            hf_confirm=gr.Checkbox(label="I reviewed the model card, license, and voice permissions, and trust this model file.",value=False)
            hf_download=gr.Button("Download selected public .pth model",variant="primary")
            hf_status=gr.Textbox(label="Download status",interactive=False)
            hf_search.click(fn=search_hf_models,inputs=[hf_query],outputs=[hf_results])
            hf_download.click(fn=download_hf_model,inputs=[hf_repo,hf_filename,hf_confirm],outputs=[model,hf_status])
        with gr.Tab("Import Voice Model"):
            gr.Markdown("## Import a trained RVC model\nUpload an inference-ready .pth file you created or are authorized to use. The model is copied into this app's local models/voices folder.\n\n**Security warning:** RVC may deserialize `.pth` pickle payloads and execute code. Only import a checkpoint from a publisher you personally trust. The acknowledgement below does not sandbox or prove the file is safe.")
            model_upload=gr.File(label="RVC model (.pth)",file_types=[".pth"],type="filepath")
            import_trust=gr.Checkbox(label="I trust this .pth checkpoint and its publisher, and understand that importing it does not sandbox the file.",value=False)
            model_upload.change(fn=lambda: False, inputs=[], outputs=import_trust)
            import_button=gr.Button("Import model",variant="primary")
            import_status=gr.Textbox(label="Import status",interactive=False)
            import_button.click(fn=import_voice_model,inputs=[model_upload,import_trust],outputs=[model,import_status])
        with gr.Tab("System"):
            gr.Markdown(f"- Python: `{sys.version.split()[0]}`\n- Voice models folder: `{VOICE_DIR}`\n- Dataset folder: `{ROOT / 'datasets'}`\n- Output folder: `{OUTPUT_DIR}`\n- Log file: `{LOG_DIR / 'oneclick-cover.log'}`")
if __name__=="__main__": demo.launch(server_name="127.0.0.1",server_port=7860,inbrowser=True,show_error=True,css=APP_CSS)
