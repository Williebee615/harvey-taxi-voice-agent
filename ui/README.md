# Local console

Run `./helper serve` from the repository root, then open http://127.0.0.1:8765. `python3 ui/ui.py` is also supported. Never serve the repository with a generic file server: the dedicated server serves only approved frontend assets and protects mutations with a local token.

The console uses actual saved run records for both explicit simulation and live Meta mode. Step/run controls invoke one tool at a time; pause stops after the in-flight tool completes. Reopen prior reviews and export their public audit JSON. Live mode transmits case files to Meta; use fictional data only.

Source frontend: root `index.html`, `app.js`, `console.css`. `docs/` contains the static preview copy; it requires a local server for execution. The legacy `ui/index.html` mirrors the root shell for compatibility.
