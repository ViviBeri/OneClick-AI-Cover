from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:7862/"


def serve() -> None:
    import gradio as gr
    import uvicorn
    from fastapi import FastAPI

    import app as product_app

    parent = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    application = gr.mount_gradio_app(
        parent,
        product_app.demo,
        path="/",
        server_name="127.0.0.1",
        server_port=7862,
        show_error=True,
        theme=gr.themes.Soft(
            primary_hue="violet",
            secondary_hue="cyan",
            neutral_hue="slate",
        ),
        css=product_app.APP_CSS,
        footer_links=[],
    )
    uvicorn.run(application, host="127.0.0.1", port=7862, log_level="error")


def main() -> int:
    if "--serve" in sys.argv:
        serve()
        return 0

    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--serve"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
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
                        f"Mounted product UI exited with code {process.returncode}."
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
                    f"Mounted product UI did not start: {last_error}"
                )

            expect(page.locator(".studio-hero")).to_be_visible(timeout=20000)
            expect(page.locator(".studio-step")).to_have_count(4)
            browser.close()

        print(
            "PRODUCT GRADIO UI WITHOUT BROKER PASSED: "
            "full app rendered under FastAPI mount.",
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
                print("--- Product UI mount server output ---")
                print(output[-8000:])


if __name__ == "__main__":
    raise SystemExit(main())
