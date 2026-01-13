import google.generativeai as genai
import os

key = "AIzaSyBp_ZT5ADJ3y5lUxePARLmoyF0N3-a3fUQ"

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
