import base64
import os
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Get Gemini API key from environment
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Initialize the Gemini client lazily
client = None

def get_gemini_client():
    global client
    if client is None:
        if not GEMINI_API_KEY:
            raise ValueError('GEMINI_API_KEY environment variable is not set')
        client = genai.Client(api_key=GEMINI_API_KEY)
    return client

def image_to_text_description(image_path: str) -> str:
    """
    Converts an image file to a text description using the Gemini vision model.
    """
    try:
        # Get the Gemini client
        gemini_client = get_gemini_client()
        
        # 1. Prepare the image part
        image_part = types.Part.from_uri(
            uri=f"file://{image_path}",
            mime_type="image/jpeg" # Assuming most uploads are jpeg/png
        )

        # 2. Call the vision model
        prompt = "Describe the product in this image in detail, focusing on color, material, style, and any text. Provide a concise, comma-separated list of keywords and a short sentence description that would be ideal for a product search query. Example: 'red, cotton, t-shirt, graphic print, vintage style, A vintage red cotton t-shirt with a faded graphic print.'"
        
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, image_part],
            config=types.GenerateContentConfig(
                max_output_tokens=300
            )
        )

        # 3. Extract the description
        description = response.text.strip()
        return description

    except APIError as e:
        print(f"Gemini API Error in image_to_text_description: {e}")
        return "Error processing image"
    except Exception as e:
        print(f"General Error in image_to_text_description: {e}")
        return "Error processing image"

def get_semantic_search_query(query: str) -> str:
    """
    Placeholder for a function that might generate a semantic search query
    or embedding from a text query.
    """
    # For now, we'll just return the query itself.
    return query

