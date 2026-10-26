# AfyaPlus Symptom Triage Engine

## 1. Project Overview

AfyaPlus is an educational AI engineering prototype that demonstrates
how a symptom-triage application can classify user-reported symptoms
and route the result for further attention.

The application follows a cloud-first architecture:
- Cloud inference uses OpenRouter through the OpenAI-compatible Python SDK.
- Local fallback uses Ollama with the `llama3.2:latest` model.
- Model responses are parsed and validated as JSON.
- If cloud inference fails, the application attempts local inference.


## 2. Project Objectives

The project demonstrates how to:

1. Engineer prompts with explicit roles, output requirements and safety guardrails.
2. enforce a consistent JSON schema for model responses.
3. Use cloud inference as the primary pathway.
4. Fall back to a locally hosted model when cloud inference fails.
5. Compare cloud and local inference latency.
6. communicate AI limitations and risks in a healthcare-related use case.

## 3. Architecture

```text
User enters symptom description
              |
      Cloud inference
       OpenRouter API
              |
       |             |
    Success        Failure
       |             |
       |             v
       |       Local inference
       |       Ollama / Llama 3.2
       |             |
              |
              v
       Parse and validate JSON
              |
  
    Return result and routing


The application tries the cloud pathway first. If that pathway fails,
it attempts local Ollama inference. If both pathways fail, it returns
a safe error response instead of inventing a triage classification.

4. Technology Stack 

- Python 3
- OpenAI-compatible Python SDK
- OpenRouter cloud API
- Ollama local inference
- Llama 3.2 local model
- HTTPX for local HTTP requests
- python-dotenv for environment configuration
- JSON for structured model output

5. Project Structure

wk1-capstone-project-afyaplus-triage-engine/
├── .env
├── .gitignore
├── app.py
├── screenshots
├── test_cloud.py
├── README.md
└── .venv/
```

The `.env` file contains local configuration and credentials. It must
not be committed to a public repository or shared in screenshots.

## 6. Setup and Configuration

### Prerequisites

- Python 3
- A Python virtual environment
- An OpenRouter API key
- Ollama installed and running
- The `llama3.2:latest` model available locally

### Activate the virtual environment

From the project directory, run:

```Terminal
source .venv/bin/activate
```

### Install the Python dependencies

```Terminal
python -m pip install openai httpx python-dotenv
```

### Configure environment variables

Create or update the local `.env` file with your own values:

```
OPENROUTER_API_KEY=your_actual_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openrouter/free
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
```

Replace the API-key placeholder locally. Never publish the actual key.

### Verify Ollama

```Terminal
ollama list
curl --max-time 5 -s http://localhost:11434/api/tags
```

Ensure that `llama3.2:latest` is available before testing local
inference.

## 7. Running the Application

Run interactively:

```Terminal
python app.py
```

Or provide a symptom description as a command-line argument:

```Terminal
python app.py "I have a mild headache and feel tired"
```

The application prints the result as JSON and displays the routing
decision, inference source and measured latency.

## 8. Prompt Engineering Iterations

### Prompt V1: Basic classification

The first prompt asks the model to classify symptoms and return JSON.

Limitation: It provides minimal guidance about output structure,
medical uncertainty and safety.

### Prompt V2: Role and safety boundaries

The second prompt identifies the application as an AfyaPlus
health-information component. It adds requirements to avoid diagnosis,
avoid invented clinical facts and identify symptoms reported by the user.

Improvement: It establishes a clearer role and introduces safety
boundaries.

## Prompt V3: Final guarded prompt

The final prompt adds explicit instructions for:
- Identifying only symptoms supported by the user's message.
- Recognising possible emergency indicators.
- Selecting an allowed routing destination.
- Avoiding unsupported diagnoses and clinical calculations.
- Handling insufficient information cautiously.
- Producing concise reasoning summaries instead of private,
  step-by-step reasoning.
- Returning only the required JSON fields and types.

Prompt V3 is used by both the cloud and local inference functions.

## 9. Required JSON Schema

The model response must contain exactly these four fields:

```json
{
  "is_critical_emergency": false,
  "detected_symptoms": ["mild headache"],
  "clinical_reasoning_summary": "A concise summary supported by the supplied message.",
  "routing_destination": "ROUTINE"
}
```

Field requirements:

| Field | Required type |
| `is_critical_emergency` | Boolean |
| `detected_symptoms` | Array of strings |
| `clinical_reasoning_summary` | Non-empty string |
| `routing_destination` | Allowed destination string |

Allowed routing destinations:

- `EMERGENCY`
- `CLINICAL_REVIEW`
- `ROUTINE`

The application uses Python's `json.loads()` to parse the model
response. It validates the exact field names, value types and routing
consistency. The cloud request uses JSON Mode, and the Ollama request
uses its JSON output format.

Runtime metadata such as inference source, latency and cloud status
is added after the original model response has passed schema validation.

## 10. API Resilience and Fallback

The cloud pathway uses a configured timeout of four seconds and
disables SDK retries. The local Ollama pathway has a separate timeout
of 300 seconds because local inference can be slower, particularly
when the model is first loaded.

When cloud inference fails, the application attempts local inference.
If local inference also fails, it returns an error and advises the user
not to rely on the application for triage.

The four-second setting is a configured cloud request timeout, not
proof that every complete application run finishes within four seconds.
Actual end-to-end timings must be measured and reported honestly.

## 11. Cloud and Local Latency Comparison

Latency is the time taken by an inference pathway to produce and
validate a result. It can vary because of network conditions, provider
load, model selection and local hardware.

Previously observed cloud runs in this development environment were:

| Run | Inference source | Measured latency |
| Cloud run 1 | OpenRouter | 168.513 seconds |
| Cloud run 2 | OpenRouter | 5.781 seconds |
| Local inference | Ollama / Llama 3.2 | Pending measurement |

These are individual observations, not benchmark averages. The
cloud timings show that the configured four-second timeout should
be verified against actual end-to-end behaviour.

Before final submission: Run a successful local inference and
record its actual `_latency_seconds` value. Then update this table
and explain the difference between cloud and local performance.
Do not invent a local measurement.

## 12. Sample Output Evidence

Include at least three real demonstration outputs in the final
submission:

1. Cloud success:A valid JSON result produced by OpenRouter.
2. Fallback success: A cloud failure followed by a valid local
   Ollama result.
3. Additional triage example:Another input demonstrating the
   application's routing and structured output.

For each example, record the input, the returned JSON, inference
source, latency and cloud status when available. Remove credentials
and any personal information from screenshots.

## 13. Risks and Limitations

- The prototype is not clinically validated.
- Model-generated classifications can be incorrect.
- A valid JSON response does not guarantee medical accuracy.
- Cloud inference depends on network connectivity and provider availability.
- Local inference depends on the local model, available memory and hardware.
- A timeout or model failure must not be interpreted as evidence that a
  person's condition is safe.
- Real deployment would require clinical validation, privacy safeguards,
  security review, monitoring and appropriate human oversight.

The system is a demonstration of AI engineering and resilience patterns,
not a substitute for professional medical assessment.

## 14. Conclusion

The AfyaPlus prototype combines prompt engineering, structured JSON
validation, cloud inference and local fallback in one application.
It demonstrates a practical approach to handling model failures while
highlighting the importance of measurable performance, reliable output
validation and safety limitations in healthcare-related AI systems.
