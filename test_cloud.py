import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Load settings from the .env file beside this script.
env_file = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_file, override=True)

# Read the OpenRouter configuration.
api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
base_url = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
)
model = os.getenv("OPENROUTER_MODEL", "openrouter/free")

# Reject missing keys and common placeholder values.




print("API key loaded: True")
print("Base URL:", base_url)
print("Model:", model)

# Connect to OpenRouter. The short timeout keeps the test bounded.
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
    timeout=4.0,
    max_retries=0,
)

try:
    # Send an actual request to the selected model.
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: AfyaPlus cloud connected",
            }
        ],
        max_tokens=100,
    )

    # Print response details to diagnose model behavior.
    choice = response.choices[0]
    print("API request: SUCCESS")
    print("Model returned:", response.model)
    print("Finish reason:", choice.finish_reason)
    print("Response:", repr(choice.message.content))

except Exception as error:
    # Show the error without displaying the API key.
    print("API request: FAILED")
    print("Error type:", type(error).__name__)
    print("Error details:", str(error)[:800])

finally:
    # Close the client connection.
    client.close()
