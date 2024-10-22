# HelpMeGPT is a Python script powered by OpenAI's GPT and utilizing OpenCV to detect a user's screen and send images to the GPT for explaining the image.
# This script will also utilize Text Highlighting to highlight the text on the screen and send it to the GPT for explaining the text.
# Goal of this is to utilize the GPT to explain the image and text to the user and help them learn or understand the content.
# we will utilize OpenAI, OpenCV, Text Higlighting Transcription and then Speech To Text and Text To Speech for additional functionality and contextual understanding.
import asyncio
import logging
from dotenv import load_dotenv
import os
from livekit.agents import AutoSubscribe, JobContext, cli, llm, WorkerOptions
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero
from screenHelp import AssistantFnc

load_dotenv()

logger = logging.getLogger("myagent")
logger.setLevel(logging.INFO)

openai_api_key = os.getenv("OPENAI_API_KEY")
name = "Andrew Rapier"
agent_name = "Ciara"

async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are a voice assistant created by LiveKit. Your interface with users will be voice. "
            "You should use short and concise responses, and avoiding usage of unpronouncable punctuation."
        ),
    )
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    fnc_ctx = AssistantFnc()

    assitant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        chat_ctx=initial_ctx,
        fnc_ctx=fnc_ctx,
    )
    assitant.start(ctx.room)

    await asyncio.sleep(1)
    await assitant.say("Hey, how can I help you today!", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))