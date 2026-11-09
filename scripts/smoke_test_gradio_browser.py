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


def click_gradio_tab(page, name: str) -> None:
    """Click a Gradio tab while tolerating transient DOM replacement."""
    last_error = None
    for _ in range(5):
        tab = page.get_by_role("tab", name=name)
        try:
            expect(tab).to_be_visible(timeout=5000)
            # Gradio can replace tab nodes during a render between Playwright's
            # actionability checks. Reacquire and dispatch the native click.
            tab.evaluate("(element) => element.click()")
            return
        except Exception as exc:
            last_error = exc
            page.wait_for_timeout(250)
    raise RuntimeError(f"Could not activate Gradio tab {name!r}: {last_error}")


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

            click_gradio_tab(page, "Import Voice Model")
            # Gradio 6 does not consistently associate the visible component label
            # with its hidden file input. Both model-preflight and import tabs accept
            # .pth files, so the final matching input is the import control.
            upload = page.locator('input[type="file"][accept*=".pth"]').last
            if upload.count() == 0:
                inputs = page.locator('input[type="file"]').evaluate_all(
                    "(elements) => elements.map((element) => ({accept: element.accept, id: element.id}))"
                )
                raise RuntimeError(f"No .pth upload input found; file inputs: {inputs}")

            with tempfile.TemporaryDirectory(prefix="gradio-import-smoke-") as temporary:
                candidate = Path(temporary) / "browser-smoke-model.pth"
                candidate.write_bytes(b"browser callback smoke test" + bytes(2048))
                upload.set_input_files(str(candidate), timeout=10000)
                import_trust = page.get_by_label(
                    "I trust this .pth checkpoint and its publisher, and understand that importing it does not sandbox the file."
                )
                import_trust.check()
                replacement_dir = Path(temporary) / "replacement"
                replacement_dir.mkdir()
                replacement = replacement_dir / "browser-smoke-model.pth"
                replacement.write_bytes(b"replacement browser smoke test" + bytes(2048))

                # Gradio replaces the file input with a file preview after upload.
                # Clear the first selection before locating the newly rendered input.
                clear_file = page.get_by_role("button", name="Clear")
                expect(clear_file.last).to_be_visible(timeout=10000)
                clear_file.last.click()
                replacement_upload = page.locator('input[type="file"][accept*=".pth"]').last
                replacement_upload.wait_for(state="attached", timeout=10000)
                replacement_upload.set_input_files(str(replacement), timeout=10000)
                expect(import_trust).not_to_be_checked(timeout=10000)
                import_trust.check()
                page.get_by_role("button", name="Import model").click()
                expect(page.get_by_label("Import status")).to_have_value(
                    "Imported browser-smoke-model.pth. You can now select it under Generate Cover.",
                    timeout=15000,
                )

            click_gradio_tab(page, "Generate Cover")
            page.get_by_role("button", name="Refresh models").click()
            expect(page.get_by_label("RVC voice model (.pth)")).to_have_value(
                "browser-smoke-model.pth", timeout=15000
            )
            # Verify the primary workflow remains usable at a narrow Android viewport.
            page.set_viewport_size({"width": 390, "height": 844})
            click_gradio_tab(page, "Generate Cover")
            expect(page.get_by_role("button", name="Generate cover")).to_be_visible()
            container_width = page.locator(".gradio-container").evaluate(
                "(element) => Math.ceil(element.getBoundingClientRect().width)"
            )
            viewport_width = page.evaluate("window.innerWidth")
            if container_width > viewport_width:
                raise RuntimeError(
                    f"Mobile layout overflows viewport: {container_width}px > {viewport_width}px"
                )

            print(
                "GRADIO 6 BROWSER SMOKE PASSED: import callback, model refresh, and 390px mobile viewport passed; "
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
