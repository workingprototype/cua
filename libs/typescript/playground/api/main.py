import json
import time
from typing import Any, Dict, List

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .utils.prompt import ClientMessage
from .utils.tools import get_current_weather

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Allow direct calls from local development
        "http://frontend:3000",  # Allow calls from the `frontend` service in Docker Compose
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all HTTP headers
)


class Request(BaseModel):
    messages: List[ClientMessage]


available_tools = {
    "get_current_weather": get_current_weather,
}


def do_stream(messages: List[Dict[str, Any]]):
    """Mock streaming function that returns a mock stream object"""
    # This is a mock implementation - in real usage this would return an OpenAI stream
    return []


def stream_text(messages: List[Dict[str, Any]], protocol: str = "data"):
    """Mock streaming text function that yields mock responses in the expected format"""

    # Check if the last message mentions weather to simulate tool calling
    last_message = messages[-1] if messages else {}
    message_content = last_message.get("content", "").lower()

    should_call_weather_tool = "weather" in message_content

    if should_call_weather_tool:
        # Mock tool call scenario
        tool_call_id = "call_mock_123"
        tool_name = "get_current_weather"
        tool_args = '{"latitude": 37.7749, "longitude": -122.4194}'

        # Yield tool call
        yield '9:{{"toolCallId":"{id}","toolName":"{name}","args":{args}}}\n'.format(
            id=tool_call_id, name=tool_name, args=tool_args
        )

        # Mock tool execution
        tool_result = available_tools[tool_name](latitude=37.7749, longitude=-122.4194)

        # Yield tool result
        yield 'a:{{"toolCallId":"{id}","toolName":"{name}","args":{args},"result":{result}}}\n'.format(
            id=tool_call_id,
            name=tool_name,
            args=tool_args,
            result=json.dumps(tool_result),
        )

        # Yield final response with tool usage
        yield 'e:{{"finishReason":"tool_calls","usage":{{"promptTokens":50,"completionTokens":25}},"isContinued":false}}\n'

    else:
        # Mock regular text response
        mock_response_parts = [
            "This is a mock response from the API. ",
            "I'm simulating the streaming behavior ",
            "that would normally come from OpenAI. ",
            "The original functionality has been preserved ",
            "but now uses mock data instead.",
        ]

        # Stream the response in chunks
        for part in mock_response_parts:
            yield "0:{text}\n".format(text=json.dumps(part))
            time.sleep(0.1)  # Small delay to simulate streaming

        # Yield end marker
        yield 'e:{{"finishReason":"stop","usage":{{"promptTokens":30,"completionTokens":20}},"isContinued":false}}\n'


@app.post("/chat")
async def handle_chat_data(request: Request, protocol: str = Query("data")):
    messages = request.messages
    # Convert to simple dict format for mock processing
    mock_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

    print("Simple log")

    response = StreamingResponse(stream_text(mock_messages, protocol))
    response.headers["x-vercel-ai-data-stream"] = "v1"
    return response


@app.get("/model")
def handle_model_pull():
    print("Hello from FastAPI handle_model_pull")
    return {"message": "Hello from FastAPI"}


@app.get("/tags")
def get_tags():
    print("Hello from FastAPI get_tags")
    return {"message": "Hello from FastAPI"}


# @app.get("/")
# def read_root():
#     print("Hello from FastAPI")
#     return {"message": "Hello from FastAPI"}
