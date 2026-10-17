import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load the .env file
load_dotenv(Path(__file__).resolve().parent / ".env")

# Read your Gemini API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Gemini API key not found in .env")

# Connect to Gemini
client = genai.Client(api_key=api_key)

def ask_gemini(prompt):
    response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents=prompt
)
    return response.text


from google.genai import types
import json

def analyze_eye_image(image_bytes, mime_type="image/jpeg"):
    prompt = """
    You are assisting EyeSpy AI, an educational
    eye-image screening prototype.

    Describe only features visible in this image:
    - Eye redness
    - Visible irritation or discharge
    - Visible cloudiness
    - Image quality and limitations

    Do not diagnose pink eye, cataracts,
    infections, or any medical condition.

    Return valid JSON with these fields:
    {
      "redness": "description",
      "irritation": "description",
      "cloudiness": "description",
      "summary": "description",
      "recommendation": "description"
    }

    Explain uncertainty. If the image is unclear,
    say so. Do not infer a healthy eye from a
    normal-looking photograph.

    Mention that eye pain, vision loss, or sudden
    vision changes require urgent medical assessment.
    """

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return json.loads(response.text)
