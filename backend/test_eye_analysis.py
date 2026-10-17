
from pathlib import Path
from google.genai import types
from gemini_service import client

image_path = Path("test_eye.jpg")

if not image_path.exists():
    print("Please add test_eye.jpg to backend/")
    raise SystemExit(1)

image_bytes = image_path.read_bytes()

prompt = """
You are assisting EyeSpy AI, an educational
eye-image screening prototype.

Describe only what is visible in this image.

Report:
1. Visible redness
2. Visible discharge or irritation
3. Visible cloudiness
4. Image quality
5. Other visible observations

Do not diagnose cataracts, pink eye, or other
medical conditions.

Explain uncertainty and recommend professional
evaluation for concerning symptoms.

Return a short, easy-to-understand report.
"""

response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents=[
        prompt,
        types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/jpeg"
        )
    ]
)

print("\n===== EYESPY AI REPORT =====\n")
print(response.text)
