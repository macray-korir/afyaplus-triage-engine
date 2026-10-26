# AfyaPlus Capstone Application
# Cloud-first triage demonstration with local Ollama fallback.
#
# Run:
#   python app.py
#   python app.py "I have a mild headache"
#
# IMPORTANT: This is an educational prototype, not a clinical decision tool.

import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from openai import OpenAI


# ---------------------------------------------------------
# 1. Load configuration and credentials safely
# ---------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env", override=True)

API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
)
MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

OLLAMA_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
).rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")

# The cloud transit timeout must not exceed four seconds.
CLOUD_TIMEOUT_SECONDS = 4.0

# Local inference may be slower, so it has its own timeout.
LOCAL_TIMEOUT_SECONDS = 300.0


# Variation 1: Basic classification instruction. Promt engineering alteration Zero-shot prompting
PROMPT_V1 = """
Classify the supplied symptoms as a possible emergency or not.
Return a JSON object describing the result.
"""

# Variation 2: Add role, allowed fields, and safety boundaries.
PROMPT_V2 = """
You are the AfyaPlus symptom-triage component for an educational
health-information application in Kenya.
Do not diagnose or invent clinical facts.
Identify symptoms explicitly described by the user.
Return a JSON object with the required AfyaPlus fields.
Recommend professional medical assessment when appropriate.
"""

# Variation 3: Final prompt with role-based instructions and guardrails.

PROMPT_V3 = """
You are AfyaPlus, a cautious symptom-triage component for an educational
health-information application in Kenya.

Your task:
- Identify symptoms explicitly reported by the user.
- Decide whether the message contains signs of a possible emergency.
- Choose a suitable routing destination.
- Use only information supported by the user's message.
- If information is insufficient, do not claim the person is safe.
- Never diagnose, invent symptoms, or make unsupported clinical calculations.
- Do not include greetings, introductions, Markdown, or conversational fluff.
- Do not reveal private step-by-step reasoning. Provide only a concise,
  evidence-based clinical reasoning summary.
- If an emergency may be occurring, recommend immediate emergency care.
- This output is a preliminary demonstration result, not a medical diagnosis.

Return only a valid JSON object matching these exact fields and types:
{
  "is_critical_emergency": false,
  "detected_symptoms": ["symptom described by the user"],
  "clinical_reasoning_summary": "Brief summary based on the supplied message",
  "routing_destination": "ROUTINE"
}

Rules:
- is_critical_emergency must be a JSON boolean.
- detected_symptoms must be an array of strings. Use [] if no symptoms
  are explicitly identified.
- clinical_reasoning_summary must be a string.
- routing_destination must be one of: "EMERGENCY", "CLINICAL_REVIEW",
  or "ROUTINE".
- For a possible emergency, set is_critical_emergency to true and
  routing_destination to "EMERGENCY".
- For uncertain or concerning symptoms that need professional assessment,
  use "CLINICAL_REVIEW".
- Use "ROUTINE" only when the limited message supports routine routing.
"""


# Validate the exact required JSON schema
REQUIRED_KEYS = {
    "is_critical_emergency",
    "detected_symptoms",
    "clinical_reasoning_summary",
    "routing_destination",
}

VALID_DESTINATIONS = {"EMERGENCY", "CLINICAL_REVIEW", "ROUTINE"}

# functions 

def validate_result(raw_text: str) -> dict:
    """Parse JSON and reject responses that do not match the required schema."""
    result = json.loads(raw_text)

    if not isinstance(result, dict):
        raise ValueError("Model output must be a JSON object.")

    if set(result.keys()) != REQUIRED_KEYS:
        raise ValueError("Output does not match the exact required JSON keys.")

    if not isinstance(result["is_critical_emergency"], bool):
        raise ValueError("Emergency flag must be a JSON boolean.")

    symptoms = result["detected_symptoms"]
    if not isinstance(symptoms, list) or not all(
        isinstance(item, str) for item in symptoms
    ):
        raise ValueError("detected_symptoms must be an array of strings.")

    summary = result["clinical_reasoning_summary"]
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("Reasoning summary must be non-empty text.")

    destination = result["routing_destination"]
    if destination not in VALID_DESTINATIONS:
        raise ValueError("Invalid routing destination.")

    # Keep emergency status and routing consistent.
    if result["is_critical_emergency"] and destination != "EMERGENCY":
        raise ValueError("Emergency cases must route to EMERGENCY.")

    if destination == "EMERGENCY":
        result["is_critical_emergency"] = True

    return result
#  Cloud pathway: OpenRouter with native JSON Mode

def run_cloud(user_message: str) -> dict:
    """Call the cloud model with a strict timeout and JSON Mode."""
    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured.")

    started = time.perf_counter()

    # Disable retries so a failed request does not silently exceed the budget.
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=CLOUD_TIMEOUT_SECONDS,
        max_retries=0,
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PROMPT_V3},
                {"role": "user", "content": user_message},
            ],
            # Native JSON Mode, as required by the assignment.
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=300,
        )

        raw_text = response.choices[0].message.content
        if not raw_text:
            raise ValueError("Cloud model returned empty content.")

        result = validate_result(raw_text)
        result["_source"] = "cloud"
        result["_latency_seconds"] = round(
            time.perf_counter() - started, 3
        )
        return result

    finally:
        client.close()


#  Local pathway: Ollama fallback


def run_local(user_message: str) -> dict:
    """Send the same final prompt to the local Ollama model."""
    started = time.perf_counter()

    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": PROMPT_V3},
            {"role": "user", "content": user_message},
        ],
        "options": {"temperature": 0, "num_predict": 300},
    }

    # httpx enforces a separate timeout for local inference.
    with httpx.Client(timeout=LOCAL_TIMEOUT_SECONDS) as client:
        response = client.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()

    body = response.json()
    raw_text = body.get("message", {}).get("content", "")

    if not raw_text:
        raise ValueError("Ollama returned empty content.")

    result = validate_result(raw_text)
    result["_source"] = "local_ollama"
    result["_latency_seconds"] = round(
        time.perf_counter() - started, 3
    )
    return result


# Run cloud first, then fall back to local on failure
def run_triage(user_message: str) -> dict:
    """Try cloud inference first; use Ollama if cloud inference fails."""
    try:
        result = run_cloud(user_message)
        result["_cloud_status"] = "success"
        return result

    except (
        httpx.TimeoutException,
        httpx.HTTPStatusError,
        httpx.RequestError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
    ) as error:
        # Log the failure type, but never log credentials or patient messages.
        print(f"Cloud pathway failed: {type(error).__name__}")
        print("Attempting local Ollama fallback...")

    except Exception as error:
        # Defensive catch for unexpected SDK/API errors.
        print(f"Unexpected cloud error: {type(error).__name__}")
        print("Attempting local Ollama fallback...")

    try:
        result = run_local(user_message)
        result["_cloud_status"] = "failed; local fallback succeeded"
        return result

    except Exception as error:
        # Report both-path failure without inventing a triage classification.
        return {
            "error": "Both cloud and local inference failed.",
            "cloud_fallback_status": "failed",
            "local_error_type": type(error).__name__,
            "next_step": (
                "Do not rely on this application for triage. "
                "Contact a qualified healthcare professional. "
                "If this may be an emergency, seek emergency help now."
            ),
        }
# Command-line entry point
if __name__ == "__main__":
    # Accept symptoms as an argument, or ask interactively.
    if len(sys.argv) > 1:
        patient_message = " ".join(sys.argv[1:]).strip()
    else:
        patient_message = input("Enter a symptom description: ").strip()

    if not patient_message:
        raise SystemExit("Please enter a symptom description.")

    final_result = run_triage(patient_message)

    # Print the parsed Python dictionary as JSON for easy inspection.
    print("\nAfyaPlus result:")
    print(json.dumps(final_result, indent=2, ensure_ascii=False))

    # Print a concise routing decision for the demonstration.
    if "routing_destination" in final_result:
        print(
            "\nRouting decision:",
            final_result["routing_destination"],
            "| Source:",
            final_result["_source"],
            "| Latency:",
            final_result["_latency_seconds"],
            "seconds",
        )
    else:
        print("\nRouting decision: NO RESULT — inference failed.")
