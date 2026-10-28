from __future__ import annotations
import logging, sys, tempfile, shutil
from pathlib import Path
import gradio as gr
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from oneclick_cover.audio_utils import mix_audio, probe_audio, transcode_to_wav
from oneclick_cover.settings import VOICE_DIR, OUTPUT_DIR, LOG_DIR
from oneclick_cover.validation import validate_audio_file, validate_voice_model
from oneclick_cover.separation import separate_vocals
from oneclick_cover.conversion import convert_voice
from oneclick_cover.training import launch_training_ui
from oneclick_cover.dataset import prepare_recordings
from oneclick_cover.settings import ROOT
for folder in (VOICE_DIR, OUTPUT_DIR, LOG_DIR): folder.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_DIR / "oneclick-cover.log", level=logging.INFO)
def models(): return sorted(p.name for p in VOICE_DIR.glob("*.pth") if p.is_file())
def refresh_models():
    choices = models()
    return gr.update(choices=choices, value=(choices[0] if choices else None))
def import_voice_model(uploaded_file):
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
        return gr.update(choices=choices, value=destination.name), f"Imported {destination.name}. You can now select it under Generate Cover."
    except Exception as exc:
        logging.exception("Voice model import failed")
        raise gr.Error(str(exc)) from exc
def prepare_training_dataset(uploaded_files, dataset_name, progress=gr.Progress()):
    try:
        progress(0.1, desc="Checking recordings")
        folder, count = prepare_recordings(uploaded_files or [], dataset_name, ROOT / "datasets")
        progress(1.0, desc="Recordings prepared")
        return str(folder), f"Prepared {count} recording(s). In the RVC training UI, use this folder path as the dataset/training folder. Review the upstream RVC preprocessing instructions before starting training."
    except Exception as exc:
        logging.exception("Dataset preparation failed")
        raise gr.Error(str(exc)) from exc

def generate(song, model, pitch, vocal_gain, instrumental_gain, fmt, progress=gr.Progress()):
    if not song: raise gr.Error("Choose an input song first.")
    if not model: raise gr.Error("Add an authorized .pth model to models/voices, then refresh.")
    try:
        source=Path(song); validate_audio_file(source); model_path=(VOICE_DIR/model).resolve()
        if model_path.parent != VOICE_DIR.resolve(): raise ValueError("Invalid voice-model selection.")
        validate_voice_model(model_path)
        job=Path(tempfile.mkdtemp(prefix="cover_",dir=OUTPUT_DIR)); wav=job/"input.wav"
        progress(0.1,desc="Preparing audio"); transcode_to_wav(source,wav)
        progress(0.25,desc="Separating vocals"); vocals,instrumental=separate_vocals(wav,job)
        progress(0.6,desc="Converting voice"); converted=job/"converted.wav"; convert_voice(vocals,converted,model_path,int(pitch))
        progress(0.85,desc="Mixing"); output=job/"cover.wav"
        mix_audio(converted,instrumental,output,float(vocal_gain),float(instrumental_gain))
        if fmt=="MP3":
            from oneclick_cover.audio_utils import export_mp3
            mp3=job/"cover.mp3"; export_mp3(output,mp3); output=mp3
        progress(1,desc="Done"); return str(output), "Saved: "+str(output)
    except Exception as e:
        logging.exception("Cover generation failed"); raise gr.Error(str(e)) from e
with gr.Blocks(title="OneClick-AI-Cover") as demo:
    gr.Markdown("# OneClick-AI-Cover\nFree, local-first AI singing-cover creator. Use only audio and voice models you are authorized to use.")
    with gr.Row():
        song=gr.File(label="Song (MP3/WAV/FLAC)",file_types=[".mp3",".wav",".flac"],type="filepath")
        model=gr.Dropdown(label="RVC voice model (.pth)",choices=models())
    refresh=gr.Button("Refresh models"); refresh.click(refresh_models, inputs=[], outputs=model)
    pitch=gr.Slider(-12,12,value=0,step=1,label="Pitch shift")
    vocal_gain=gr.Slider(0.2,2,value=1,step=0.05,label="Vocal gain")
    instrumental_gain=gr.Slider(0.2,2,value=0.85,step=0.05,label="Instrumental gain")
    fmt=gr.Radio(["WAV","MP3"],value="WAV",label="Export format")
    go=gr.Button("Generate cover",variant="primary"); audio=gr.Audio(type="filepath"); status=gr.Textbox()
    go.click(generate,inputs=[song,model,pitch,vocal_gain,instrumental_gain,fmt],outputs=[audio,status])
    with gr.Tab("Import Voice Model"):
        gr.Markdown("## Import a trained RVC model\nUpload an inference-ready .pth file you created or are authorized to use. Large files may take time to upload. The model is copied into this app's local models/voices folder.")
        model_upload = gr.File(label="RVC model (.pth)", file_types=[".pth"], type="filepath")
        import_button = gr.Button("Import model", variant="primary")
        import_status = gr.Textbox(label="Import status", interactive=False)
        import_button.click(fn=import_voice_model, inputs=[model_upload], outputs=[model, import_status])
    with gr.Tab("Prepare Voice Recordings"):
        gr.Markdown("""## Prepare your own voice recordings
Upload recordings of your own voice, or recordings you have explicit permission to use. The app converts each file to mono 44.1 kHz WAV and stores them in a local dataset folder. It does not upload them to a cloud service.

- Use clean, dry recordings with one speaker.
- Avoid background music, reverb, clipping, and other speakers.
- This step prepares files only; it does not start training automatically.
- FFmpeg must be installed and available on PATH for conversion.
""")
        dataset_name = gr.Textbox(label="Dataset folder name", value="MyVoice")
        recording_files = gr.File(label="Recordings (select multiple)", file_count="multiple", file_types=[".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac"], type="filepath")
        prepare_button = gr.Button("Prepare recordings", variant="primary")
        dataset_path = gr.Textbox(label="Prepared dataset path (copy into RVC training UI)", interactive=False)
        dataset_status = gr.Textbox(label="Preparation status", interactive=False)
        prepare_button.click(fn=prepare_training_dataset, inputs=[recording_files, dataset_name], outputs=[dataset_path, dataset_status])
    with gr.Tab("Train My Voice (Experimental)"):
        gr.Markdown("""## Train a voice model from your own recordings

This opens the upstream RVC training interface locally. It is an advanced workflow, not yet a one-click trainer.

1. Prepare clean recordings of the voice you have permission to train (typically at least 10–30 minutes; more clean material may help).
2. Avoid music, reverb, background voices, clipping, and long silences.
3. Click **Open RVC Training UI** and follow its dataset, preprocessing, feature extraction, training, and index steps.
4. Export the resulting inference model and place the .pth file in models/voices/, then return to Generate Cover and refresh models.

**Hardware warning:** Training is much more demanding than inference. A low-end CPU-only PC may take many hours or days and can run out of RAM. An NVIDIA GPU is strongly recommended. Do not train on another person's voice without consent.
""")
        launch_train = gr.Button("Open RVC Training UI", variant="primary")
        train_status = gr.Textbox(label="Training UI status", interactive=False)
        launch_train.click(fn=launch_training_ui, inputs=[], outputs=[train_status])
if __name__=="__main__": demo.launch(server_name="127.0.0.1",server_port=7860,inbrowser=True,show_error=True)
