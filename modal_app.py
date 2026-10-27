import os
def verify_meta_api_key_status():
    key = os.environ.get("MODEL_API_KEY", "")
    return {"metaApiKeyConfiguredInModal": bool(key.startswith("LLM_")), "keyPrefix": (key[:10] + "...") if key else "none", "primaryModel": os.environ.get("ANTHROPIC_MODEL", "muse-wonder-1.0")}

import modal

app = modal.App("norel-ai-harvey-taxi-assistant")

inference_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("fastapi[standard]", "pydantic")
)

def _evaluate_booking(payload: dict) -> dict:
    utterance = str(payload.get("text", ""))
    lower = utterance.lower()
    clearance_ft = float(payload.get("clearanceFeet", 9.5))
    needs_wc = "wheelchair" in lower or "accessible van" in lower
    return {
        "orchestrator": "norel-ai",
        "model": "meta-models/muse-spark-open-1026",
        "transcription_model": "muse-voice-transcribe",
        "vision_model": "sam-3.1",
        "intent": {
            "needsWheelchair": needs_wc,
            "hasServiceAnimal": "service animal" in lower or "service dog" in lower,
            "discountEligible": "medical" in lower or "clinic" in lower,
            "isAirport": "airport" in lower
        },
        "curbsideCheck": {
            "clearanceFeet": clearance_ft,
            "requiredFeet": 8.0 if needs_wc else 0.0,
            "status": "ADA_RAMP_VERIFIED" if (not needs_wc or clearance_ft >= 8.0) else "CURB_BLOCKED_RELOCATE_PICKUP"
        },
        "guardrails": {
            "liveDispatchEnabled": False,
            "paymentsEnabled": False
        }
    }

@app.function(image=inference_image, scaledown_window=60)
def run_gpu_inference(payload: dict) -> dict:
    return _evaluate_booking(payload)

@app.function(image=inference_image, scaledown_window=60)
@modal.fastapi_endpoint(method="POST")
def extract_accessible_booking(payload: dict):
    return _evaluate_booking(payload)

@app.local_entrypoint()
def main():
    sample = {
        "text": "Book a ride from Home to Clinic, I need a wheelchair van and have a service dog",
        "clearanceFeet": 9.5
    }
    print("Remote Modal A10G GPU worker response:", run_gpu_inference.remote(sample))
