import google.generativeai as genai
import os

key = os.getenv("GEMINI_API_KEY")

try:
    print("Configuring Gemini...")
    genai.configure(api_key=key)
    print("Init Model...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Generating...")
    response = model.generate_content("Hello")
    print("Response:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
