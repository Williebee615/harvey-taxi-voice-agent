"""Deploy the current agent console to Modal; no GPU is needed for API reasoning."""
from pathlib import Path
import modal

ROOT = Path(__file__).resolve().parent
app = modal.App('harvey-healthcare-review')
image = modal.Image.debian_slim(python_version='3.11').pip_install('fastapi', 'httpx')
# Explicit source allowlist: never upload .env, local runs, or personal files.
for folder in ('agent_kit', 'harvey_agent', 'verification', 'ui', 'cases'):
    image = image.add_local_dir(str(ROOT / folder), remote_path='/app/' + folder,
        ignore=['__pycache__', '*.pyc', '.env', '.env.*'])
for asset in ('index.html', 'app.js', 'console.css'):
    image = image.add_local_file(str(ROOT / asset), remote_path='/app/' + asset)
volume = modal.Volume.from_name('harvey-healthcare-runs', create_if_missing=True)

# Stay up for 15 idle minutes so a reviewer's open page and held Meta transcript survive normal pauses.
@app.function(image=image, secrets=[modal.Secret.from_name('harvey-healthcare-demo')],
              volumes={'/app/workspace': volume}, max_containers=1, timeout=240,
              scaledown_window=900)
@modal.concurrent(max_inputs=1)
@modal.asgi_app()
def console():
    import sys
    sys.path.insert(0, '/app')
    from ui.modal_console import create_app
    return create_app('/app', commit=volume.commit)
