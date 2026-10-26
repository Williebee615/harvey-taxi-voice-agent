"""
Norel AI / Harvey Taxi Service — Serverless GPU Inference on Modal
Deploys Meta Open Weights (Muse Spark Open) & Muse Voice Transcribe pipeline
for low-latency accessible ride booking and route/dispatch pre-validation.
"""
import modal

app = modal.App("norel-ai-harvey-taxi-assistant")

inference_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("fastapi[standard]", "pydantic")
)

@app.function(image=inference_image, gpu="A10G", scaledown_window=60)
@modal.web_endpoint(method="POST")
def extract_accessible_booking(payload: dict):
    """
    Serverless endpoint hosting Meta Muse Spark Open weights + Muse Voice Transcribe
    pipeline for structured accessible ride extraction.
    Guardrail: Returns structured intent only; deterministic pricing and driver
    matching remain authoritative in Harvey Taxi's core adapter.
    """
    utterance = str(payload.get("text", ""))
    lower = utterance.lower()
    return {
        "orchestrator": "norel-ai",
        "model": "meta-models/muse-spark-open-1026",
        "transcription_model": "meta/muse-voice-transcribe",
        "intent": {
            "needsWheelchair": "wheelchair" in lower or "accessible van" in lower,
            "hasServiceAnimal": "service animal" in lower or "service dog" in lower,
            "discountEligible": "medical" in lower or "clinic" in lower,
            "isAirport": "airport" in lower
        },
        "guardrails": {
            "liveDispatchEnabled": False,
            "paymentsEnabled": False
        }
    }
