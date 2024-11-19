import os
import pyautogui
import cv2
import numpy as np
import aiohttp  # Change to aiohttp for async requests
import base64
from openai import OpenAI
from dotenv import load_dotenv
import logging
import asyncio

logger = logging.getLogger("ScreenHelp")
logger.setLevel(logging.INFO)
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

class AssistantScreenFnc:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def explain_concept(self):
        logger.info("Explaining screen concept")
        try:
            async with self._lock:
                # Take screenshot in executor to prevent blocking
                image = await asyncio.get_event_loop().run_in_executor(
                    None, pyautogui.screenshot
                )
                
                # Convert image in executor
                image_array = np.array(image)
                image = await asyncio.get_event_loop().run_in_executor(
                    None, cv2.cvtColor, image_array, cv2.COLOR_RGB2BGR
                )
                
                in_memory_path = "in_memory.png"
                await asyncio.get_event_loop().run_in_executor(
                    None, cv2.imwrite, in_memory_path, image
                )
                
                message = await explain_with_ai(in_memory_path)
                return message
        except Exception as e:
            logger.error(f"Error in explain_concept: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    async def get_highlighted_text(self):
        logger.info("Getting highlighted text")
        return "Highlighted text functionality not implemented yet."

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def explain_with_ai(image_path):
    logger.info(f"Explaining image: {image_path}")
    try:
        # Encode image in executor to prevent blocking
        base64_image = await asyncio.get_event_loop().run_in_executor(
            None, encode_image, image_path
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_api_key}"
        }

        payload = {
            "model": "gpt-4o-mini",  # Keep your preferred model
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

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
            except asyncio.TimeoutError:
                logger.warning("Request timed out, retrying without timeout")
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error in API request: {str(e)}")
        return f"An error occurred while processing the image: {str(e)}"

