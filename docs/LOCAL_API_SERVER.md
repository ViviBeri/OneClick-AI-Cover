# Local API server lifecycle

`oneclick_cover.api_server.LocalApiServer` owns the authenticated FastAPI server and, by default, its single-worker job runner.

- Generates a fresh `secrets.token_urlsafe(32)` bearer token for each launch.
- Binds a pre-bound ephemeral TCP socket to `127.0.0.1` only, avoiding a port-selection race.
- Disables Uvicorn access logs and server-identifying response headers.
- Waits for server startup and fails closed on startup timeout.
- Stops the server, clears the in-memory token, and shuts down the runner it created.
- Supports context-manager use for integrations that have a reliable application shutdown boundary.

The token property is an in-process integration seam, not a browser delivery mechanism. Do not embed the token in a URL, log it, put it in a static HTML page, or expose it to arbitrary origins. The desktop entrypoint now starts this API server before Gradio and stops it when Gradio exits or startup fails. The API token remains in process memory and is not passed to the browser. The current Gradio UI does not call the API yet; token delivery, browser-origin/CSRF protections, and upload handling must be designed and tested before enabling browser-to-API requests.

Running Demucs/RVC subprocesses are not interrupted by runner shutdown. Shutdown may wait for the active task to finish. Queued-job cancellation remains the only cancellation behavior.
