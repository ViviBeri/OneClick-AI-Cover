from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:7860/"


def main() -> int:
    env = os.environ.copy()
    env["GRADIO_ANALYTICS_ENABLED"] = "False"
    env["PYTHONUNBUFFERED"] = "1"
    imported_model = ROOT / "models" / "voices" / "browser-smoke-model.pth"
    imported_model.parent.mkdir(parents=True, exist_ok=True)
    if imported_model.exists():
        raise RuntimeError(f"Refusing to overwrite existing test model: {imported_model}")
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "app.py")],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        deadline = time.monotonic() + 60
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            last_error = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(
                        f"Gradio app exited early with code {process.returncode}."
                    )
                try:
                    response = page.goto(URL, wait_until="domcontentloaded", timeout=3000)
                    if response and response.status == 200:
                        break
                except Exception as exc:
                    last_error = str(exc)
                    time.sleep(1)
            else:
                raise TimeoutError(f"Gradio app did not start: {last_error}")

            page.get_by_role("tab", name="Import Voice Model").click()
            upload = page.get_by_label("RVC model (.pth)").last
            with tempfile.TemporaryDirectory(prefix="gradio-import-smoke-") as temporary:
                candidate = Path(temporary) / "browser-smoke-model.pth"
                candidate.write_bytes(b"browser callback smoke test" + bytes(2048))
                upload.set_input_files(str(candidate))
                page.get_by_role("button", name="Import model").click()
                expect(page.get_by_label("Import status")).to_have_value(
                    "Imported browser-smoke-model.pth. You can now select it under Generate Cover.",
                    timeout=15000,
                )

            page.get_by_role("tab", name="Generate Cover").click()
            page.get_by_role("button", name="Refresh models").click()
            expect(page.get_by_label("RVC voice model (.pth)")).to_have_value(
                "browser-smoke-model.pth", timeout=15000
            )
            print(
                "GRADIO 6 BROWSER SMOKE PASSED: import callback copied the test model; "
                "refresh callback exposed it in the voice-model selector.",
                flush=True,
            )
            browser.close()
        return 0
    finally:
        imported_model.unlink(missing_ok=True)
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
                print("--- Gradio app output ---")
                print(output[-12000:])


if __name__ == "__main__":
    raise SystemExit(main())
