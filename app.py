from __future__ import annotations
import logging, sys, tempfile
from pathlib import Path
import gradio as gr
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from oneclick_cover.audio_utils import mix_audio, probe_audio, transcode_to_wav
from oneclick_cover.settings import VOICE_DIR, OUTPUT_DIR, LOG_DIR
from oneclick_cover.validation import validate_audio_file, validate_voice_model
from oneclick_cover.separation import separate_vocals
from oneclick_cover.conversion import convert_voice
for folder in (VOICE_DIR, OUTPUT_DIR, LOG_DIR): folder.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_DIR / "oneclick-cover.log", level=logging.INFO)
def models(): return sorted(p.name for p in VOICE_DIR.glob("*.pth") if p.is_file())
def generate(song, model, pitch, vocal_gain, instrumental_gain, fmt, progress=gr.Progress()):
    if not song: raise gr.Error("Choose an input song first.")
    if not model: raise gr.Error("Add an authorized .pth model to models/voices, then refresh.")
    try:
        source=Path(song); validate_audio_file(source); model_path=(VOICE_DIR/model).resolve(); validate_voice_model(model_path)
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
    refresh=gr.Button("Refresh models"); refresh.click(lambda: gr.Dropdown(choices=models(),value=(models() or [None])[0]),outputs=model)
    pitch=gr.Slider(-12,12,value=0,step=1,label="Pitch shift")
    vocal_gain=gr.Slider(0.2,2,value=1,step=0.05,label="Vocal gain")
    instrumental_gain=gr.Slider(0.2,2,value=0.85,step=0.05,label="Instrumental gain")
    fmt=gr.Radio(["WAV","MP3"],value="WAV",label="Export format")
    go=gr.Button("Generate cover",variant="primary"); audio=gr.Audio(type="filepath"); status=gr.Textbox()
    go.click(generate,inputs=[song,model,pitch,vocal_gain,instrumental_gain,fmt],outputs=[audio,status])
    gr.Markdown("Setup: double-click install.bat, then run.bat. Model training is not implemented in this starter build.")
if __name__=="__main__": demo.launch(server_name="127.0.0.1",server_port=7860,inbrowser=True,show_error=True)
