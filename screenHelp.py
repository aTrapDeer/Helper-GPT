import os
import pyautogui
import cv2
import numpy as np
import requests
import base64
from openai import OpenAI
from livekit.agents import llm
from dotenv import load_dotenv
import logging

logger = logging.getLogger("ScreenHelp")
logger.setLevel(logging.INFO)
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

class AssistantFnc(llm.FunctionContext):
    def __init__(self) -> None:
        super().__init__()

    @llm.ai_callable(description="Explain my screen for me.")
    async def explain_concept(self):
        logger.info("Explaining screen concept")
        # Capture screenshot
        image = pyautogui.screenshot()
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Save screenshot
        in_memory_path = "in_memory.png"
        cv2.imwrite(in_memory_path, image)
        
        # Call explain_with_ai with the correct parameters
        message = explain_with_ai(in_memory_path)
        return message

    @llm.ai_callable(description="Get highlighted text from the screen.")
    async def get_highlighted_text(self):
        # Implement logic to get highlighted text from the screen
        logger.info("Getting highlighted text")
        return "Highlighted text functionality not implemented yet."

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def explain_with_ai(image_path):
    logger.info(f"Explaining image: {image_path}")
    # Encode the image
    base64_image = encode_image(image_path)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "As a teacher, Explain the following image to me. Keep it short and concise. Don't include an overall conclusion. Just explain the image."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 700
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in API request: {str(e)}")
        return f"An error occurred while processing the image: {str(e)}"
