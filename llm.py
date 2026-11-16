
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODEL = "gemini-3.5-flash-lite"

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)


def generate_response(
    prompt: str,
    system_instruction: str = None,
    history: list = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    top_k: int = None,
    top_p: float = None,
    max_output_tokens: int = 2048
) -> str:

    # Build generation configuration
    config_params = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens
    }

    if system_instruction is not None:
        config_params["system_instruction"] = system_instruction

    if top_k is not None:
        config_params["top_k"] = top_k

    if top_p is not None:
        config_params["top_p"] = top_p

    generation_config = types.GenerateContentConfig(
        **config_params
    )

    # Convert conversation history into Gemini content objects
    contents = []

    if history:
        for message in history:
            role = message["role"]

            # Map assistant role to Gemini's model role
            if role == "assistant":
                role = "model"

            contents.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part.from_text(
                            text=message["content"]
                        )
                    ]
                )
            )

    # Add the latest user prompt
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )
    )

    # Generate response
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generation_config
    )

    return response.text


# Generate response with tools
def generate_with_tools(
    prompt: str,
    tools: list,
    system_instruction: str = None,
    temperature: float = 0.2
) -> str:

    config = types.GenerateContentConfig(
        tools=tools,
        temperature=temperature,
        system_instruction=system_instruction
    )

    chat = client.chats.create(
        model=DEFAULT_MODEL,
        config=config
    )

    response = chat.send_message(prompt)

    return response.text

    
