import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel

load_dotenv()

def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL") or "gemini-2.5-flash-lite"


def get_model(model_name: str | None = None) -> OpenAIChatCompletionsModel:
    """
    Configures and returns the OpenAIChatCompletionsModel pointing to Google's
    Gemini endpoint via its OpenAI-compatible API interface.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please add GEMINI_API_KEY=your_key to your .env file."
        )

    # Google Gemini OpenAI-compatible client
    gemini_client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    return OpenAIChatCompletionsModel(
        model=model_name or get_model_name(),
        openai_client=gemini_client,
    )
