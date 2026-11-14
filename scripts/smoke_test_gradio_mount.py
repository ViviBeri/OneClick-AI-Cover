from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:7861/"


def serve() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    import gradio as gr
    import uvicorn
    from fastapi import FastAPI

    from oneclick_cover.browser_broker import BrowserSessionStore, create_browser_broker_app
    from oneclick_cover.jobs import LocalJobStore
    from oneclick_cover.runner import LocalJobRunner

    with gr.Blocks() as demo:
        source = gr.Textbox(label="Input")
        output = gr.Textbox(label="Output")
        submit = gr.Button("Echo")
        submit.click(lambda value: value, inputs=source, outputs=output)

    runner = LocalJobRunner(store=LocalJobStore())
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    create_browser_broker_app(
        runner,
        session_store=BrowserSessionStore(),
        upload_dir=ROOT / "tmp" / "mount-smoke-uploads",
        voice_dir=ROOT / "tmp" / "mount-smoke-voices",
        output_dir=ROOT / "tmp" / "mount-smoke-outputs",
        expected_host="127.0.0.1:7861",
        expected_origin=URL.rstrip("/"),
        app=app,
    )
    application = gr.mount_gradio_app(
        app, demo, path="/", server_name="127.0.0.1",
        server_port=7861, show_error=True, footer_links=[]
    )
    uvicorn.run(application, host="127.0.0.1", port=7861, log_level="error")


def main() -> int:
    if "--serve" in sys.argv:
        serve()
        return 0

    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--serve"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    try:
        deadline = time.monotonic() + 45
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            last_error = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(
                        f"Minimal mounted app exited with code {process.returncode}."
                    )
                try:
                    response = page.goto(
                        URL, wait_until="domcontentloaded", timeout=2500
                    )
                    if response and response.status == 200:
                        break
                except Exception as exc:
                    last_error = str(exc)
                    time.sleep(0.5)
            else:
                raise TimeoutError(
                    f"Minimal mounted app did not start: {last_error}"
                )

            expect(page.get_by_label("Input")).to_be_visible(timeout=20000)
            page.get_by_label("Input").fill("broker mount works")
            page.get_by_role("button", name="Echo").click()
            expect(page.get_by_label("Output")).to_have_value(
                "broker mount works", timeout=15000
            )
            browser.close()

        print(
            "MINIMAL FASTAPI + BROKER + GRADIO MOUNT PASSED: "
            "root route rendered and browser callback completed.",
            flush=True,
        )
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.stdout:
            output = process.stdout.read()
            if output.strip():
                print("--- Minimal mount server output ---")
                print(output[-8000:])


if __name__ == "__main__":
    raise SystemExit(main())
