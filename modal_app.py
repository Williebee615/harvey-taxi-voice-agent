"""Optional Modal deployment of the same evidence engine. No GPU or model claims.

Install Modal separately. This exposes fixture verification only; use the local
console/CLI for the model-driven workflow. Deploying this is an explicit action.
"""
from pathlib import Path
import modal

ROOT = Path(__file__).resolve().parent
app = modal.App('harvey-taxi-fixture-verifier')
image = modal.Image.debian_slim(python_version='3.11').add_local_dir(
    str(ROOT), remote_path='/app', ignore=['.git', '.env', '.env.*', '__pycache__', 'workspace'])


@app.function(image=image)
def verify_fixture(case_name: str):
    import sys
    sys.path.insert(0, '/app')
    from agent_kit.evidence import inspect
    return {'execution': 'CPU_FIXTURE_VERIFICATION', 'model_invoked': False,
            'dispatch_enabled': False, **inspect('/app', case_name)}


@app.local_entrypoint()
def main():
    print(verify_fixture.remote('harvey-taxi-ada-doctor-visit'))
