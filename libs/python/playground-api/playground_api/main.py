import json
import time
import base64
import asyncio
import hashlib
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

from playground_api.utils.prompt import ClientMessage
from playground_api.utils.tools import get_current_weather

# Import Computer and Agent classes
from computer import Computer, VMProviderType
from agent import ComputerAgent, AgentLoop, LLM, LLMProvider
from agent.core.callbacks import DefaultCallbackHandler
import logging
import queue
import threading

app = FastAPI(debug=True)

# Add validation error handler
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    print(f"Validation error: {exc}")
    print(f"Request URL: {request.url}")
    print(f"Request method: {request.method}")
    try:
        body = await request.body()
        print(f"Request body: {body.decode()}")
    except:
        print("Could not read request body")
    return HTTPException(status_code=422, detail=str(exc))

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


class AgentConfig(BaseModel):
    loop: str  # "OPENAI", "ANTHROPIC", "OMNI", "UITARS"
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    save_trajectory: Optional[bool] = True
    verbosity: Optional[int] = logging.INFO
    use_oaicompat: Optional[bool] = False
    provider_base_url: Optional[str] = None
    provider_api_key: Optional[str] = None


class ComputerConfig(BaseModel):
    provider: str
    name: str
    os: str
    api_key: str


class AgentRequest(BaseModel):
    messages: List[ClientMessage]
    agent: AgentConfig
    computer: ComputerConfig


# Global screenshot queue for each agent session
screenshot_queues: Dict[str, queue.Queue] = {}


class PlaygroundScreenshotHandler(DefaultCallbackHandler):
    """Custom handler that adds screenshots to a queue for streaming."""

    def __init__(self, agent_hash: str):
        """Initialize with agent hash to identify the queue.

        Args:
            agent_hash: Hash identifying the agent session
        """
        self.agent_hash = agent_hash
        # Create queue for this agent session if it doesn't exist
        if agent_hash not in screenshot_queues:
            screenshot_queues[agent_hash] = queue.Queue()
        print(f"PlaygroundScreenshotHandler initialized for agent {agent_hash}")

    async def on_screenshot(
        self,
        screenshot_base64: str,
        action_type: str = "",
        parsed_screen: Optional[dict] = None,
    ) -> None:
        """Add screenshot to queue when a screenshot is taken.

        Args:
            screenshot_base64: Base64 encoded screenshot
            action_type: Type of action that triggered the screenshot
            parsed_screen: Optional parsed screen data
        """
        try:
            screenshot_data = {
                "type": "screenshot",
                "screenshot_base64": screenshot_base64,
                "action_type": action_type,
                "timestamp": time.time()
            }
            
            # Add to queue for this agent session
            if self.agent_hash in screenshot_queues:
                screenshot_queues[self.agent_hash].put(screenshot_data)
                print(f"Screenshot added to queue for agent {self.agent_hash}, action: {action_type}")
            else:
                print(f"Warning: No queue found for agent {self.agent_hash}")
                
        except Exception as e:
            print(f"Error in screenshot handler: {e}")


available_tools = {
    "get_current_weather": get_current_weather,
}

# Global instances cache
computer_instances: Dict[str, Computer] = {}
agent_instances: Dict[str, ComputerAgent] = {}


def get_computer_hash(config: ComputerConfig) -> str:
    """Generate a hash for computer configuration to cache instances."""
    config_str = f"{config.provider}_{config.name}_{config.os}_{config.api_key}"
    return hashlib.md5(config_str.encode()).hexdigest()


def get_agent_hash(agent_config: AgentConfig, computer_hash: str) -> str:
    """Generate a hash for agent configuration to cache instances."""
    config_str = f"{agent_config.loop}_{agent_config.model}_{computer_hash}"
    return hashlib.md5(config_str.encode()).hexdigest()


async def get_or_create_computer(config: ComputerConfig) -> Computer:
    """Get or create a computer instance based on configuration."""
    computer_hash = get_computer_hash(config)
    
    if computer_hash in computer_instances:
        return computer_instances[computer_hash]
    
    # Create new computer instance
    computer = None
    os_type_map = {
        "ubuntu": "linux",
        "linux": "linux",
        "windows": "windows", 
        "macos": "macos",
    }
    os_type = os_type_map.get(config.os, "linux")
    
    if config.provider == "host-computer":
        # Host computer configuration
        computer = Computer(
            use_host_computer_server=True,
            os_type=os_type, # type: ignore[literal-mismatch]
            verbosity=logging.INFO
        )
        
    elif config.provider == "windows-sandbox":
        computer = Computer(
            provider_type=VMProviderType.WINSANDBOX,
            os_type="windows",
            verbosity=logging.INFO
        )
        
    elif config.provider == "lume":
        computer = Computer(
            provider_type=VMProviderType.LUME,
            os_type=os_type, # type: ignore[literal-mismatch]
            name=config.name,
            verbosity=logging.INFO
        )
        
    elif config.provider == "cua-cloud":
        computer = Computer(
            provider_type=VMProviderType.CLOUD,
            os_type=os_type, # type: ignore[literal-mismatch]
            name=config.name,
            verbosity=logging.INFO,
            api_key=config.api_key,
        )
        
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {config.provider}")
    
    if computer is None:
        raise HTTPException(status_code=500, detail="Failed to create computer instance")
    
    # Initialize the computer
    await computer.run()
    
    # Cache the instance
    computer_instances[computer_hash] = computer
    
    return computer


async def get_or_create_agent(agent_config: AgentConfig, computer_config: ComputerConfig) -> ComputerAgent:
    """Get or create an agent instance based on configuration."""
    computer_hash = get_computer_hash(computer_config)
    agent_hash = get_agent_hash(agent_config, computer_hash)
    
    computer = await get_or_create_computer(computer_config)

    if agent_hash in agent_instances:
        return agent_instances[agent_hash]
    
    # Map agent loop string to enum
    loop_map = {
        "OPENAI": AgentLoop.OPENAI,
        "ANTHROPIC": AgentLoop.ANTHROPIC,
        "OMNI": AgentLoop.OMNI,
        "UITARS": AgentLoop.UITARS
    }
    
    agent_loop = loop_map.get(agent_config.loop)
    if agent_loop is None:
        raise HTTPException(status_code=400, detail=f"Unsupported agent loop: {agent_config.loop}")
    
    provider_prefixes = {
        "huggingface/": LLMProvider.HUGGINGFACE,
    }

    # Determine provider based on model prefix
    provider = None
    model_name = agent_config.model
    for prefix, provider in provider_prefixes.items():
        if model_name.startswith(prefix):
            provider = provider
            model_name = model_name[len(prefix):]
            break

    # Determine provider based on agent loop and model
    if provider is None:
        if agent_config.loop == "OPENAI":
            provider = LLMProvider.OPENAI
        elif agent_config.loop == "ANTHROPIC":
            provider = LLMProvider.ANTHROPIC
        elif agent_config.loop == "OMNI":
            # OMNI can use various providers, determine by model
            if "claude" in model_name.lower():
                provider = LLMProvider.ANTHROPIC
            elif "gpt" in model_name.lower():
                provider = LLMProvider.OPENAI
            else:
                provider = LLMProvider.OPENAI  # Default
        elif agent_config.loop == "UITARS":
            import platform
            is_mac = platform.system() == "Darwin"
            if is_mac:
                provider = LLMProvider.MLXVLM
            else:
                provider = LLMProvider.HUGGINGFACE
    
    if provider is None:
        raise HTTPException(status_code=400, detail=f"Could not determine provider for loop: {agent_config.loop}")
    
    # Get API key from agent config
    api_key = agent_config.provider_api_key
    
    # Create LLM instance
    llm_kwargs = {
        "provider": provider,
        "name": model_name
    }
    
    if agent_config.use_oaicompat and agent_config.provider_base_url:
        llm_kwargs["provider"] = LLMProvider.OAICOMPAT
        llm_kwargs["provider_base_url"] = agent_config.provider_base_url
    
    llm = LLM(**llm_kwargs)
    
    # Create agent instance
    agent = ComputerAgent(
        computer=computer,
        loop=agent_loop,
        model=llm,
        api_key=api_key,
        save_trajectory=agent_config.save_trajectory or True,
        only_n_most_recent_images=3,  # Default value
        verbosity=agent_config.verbosity or logging.INFO,
    )
    
    await agent.__aenter__() # Initialize callback handlers

    # Add screenshot handler to the agent's loop if available
    if hasattr(agent, "_loop") and agent._loop is not None:
        print(f"DEBUG - Adding screenshot handler to agent loop for {agent_hash}")
        
        # Create the screenshot handler
        screenshot_handler = PlaygroundScreenshotHandler(agent_hash)
        
        # Add the handler to the callback manager if it exists
        if (
            hasattr(agent._loop, "callback_manager")
            and agent._loop.callback_manager is not None
        ):
            agent._loop.callback_manager.add_handler(screenshot_handler)
            print(f"DEBUG - Screenshot handler added to callback manager for {agent_hash}")
        else:
            print(f"WARNING - Callback manager not found or is None for loop type: {type(agent._loop)}")
    
    # Cache the instance
    agent_instances[agent_hash] = agent
    
    return agent


async def stream_agent_response(agent: ComputerAgent, message: str, agent_hash: str):
    """Stream responses from the ComputerAgent."""
    try:
        # Stream responses from the agent
        async for result in agent.run(message):
            # Check for screenshots in the queue and yield them
            if agent_hash in screenshot_queues:
                try:
                    while True:
                        screenshot_data = screenshot_queues[agent_hash].get_nowait()
                        # Yield screenshot as annotation data
                        yield f"2:{json.dumps([screenshot_data])}\n"
                except queue.Empty:
                    pass  # No screenshots in queue, continue
            
            print(f"DEBUG - Agent response ------- START")
            from pprint import pprint
            pprint(result)
            print(f"DEBUG - Agent response ------- END")
            
            # Handle direct content (simple text response)
            if result.get("content"):
                content = result.get("content", "")
                
                # TODO: consider removing the "Task completed successfully." direct message
                if content == "Task completed successfully.":
                    continue
                
                # Yield text part in AI SDK format
                yield f"0:{json.dumps(content)}\n"
            
            # Handle complex output structure
            elif result.get("output"):
                outputs = result.get("output", [])
                for output in outputs:
                    if output.get("type") == "message":
                        # Handle message type outputs
                        content = output.get("content", [])
                        for content_part in content:
                            if content_part.get("text"):
                                text = content_part.get("text", "")
                                
                                # Yield text part
                                yield f"0:{json.dumps(text)}\n"
                    
                    elif output.get("type") == "reasoning":
                        # Handle reasoning outputs
                        # Check if it's OpenAI reasoning with summary
                        summary_content = output.get("summary", [])
                        if summary_content:
                            for summary_part in summary_content:
                                if summary_part.get("type") == "summary_text":
                                    reasoning_text = summary_part.get("text", "")
                                    # Yield reasoning part (g: format)
                                    yield f"g:{json.dumps(reasoning_text)}\n"
                        else:
                            # Handle direct reasoning text
                            reasoning_text = output.get("text", "")
                            if reasoning_text:
                                # Yield reasoning part (g: format)
                                yield f"g:{json.dumps(reasoning_text)}\n"
                    
                    elif output.get("type") == "computer_call":
                        # Handle computer action calls
                        action = output.get("action", {})
                        action_type = action.get("type", "")
                        if action_type:
                            # Create a descriptive message about the action
                            action_title = f"🛠️ Performing {action_type}"
                            if action.get("x") and action.get("y"):
                                action_title += f" at ({action['x']}, {action['y']})"
                            
                            # Yield the action details as data
                            action_data = {
                                "type": "computer_action",
                                "action": action,
                                "title": action_title
                            }
                            yield f"2:{json.dumps([action_data])}\n"
            
            # Check if this is the final response
            if result.get("finish_reason") or result.get("done"):
                # Yield finish step part
                finish_reason = result.get("finish_reason", "stop")
                usage = result.get("usage", {"promptTokens": 0, "completionTokens": 0})
                yield f'e:{{"finishReason":"{finish_reason}","usage":{json.dumps(usage)},"isContinued":false}}\n'
                break
                
    except Exception as e:
        print(f"Error in agent streaming: {e}")
        import traceback
        traceback.print_exc()
        # Yield error response
        yield f"3:{json.dumps(f'Error: {str(e)}')}\n"
        yield f'e:{{"finishReason":"error","usage":{{"promptTokens":0,"completionTokens":0}},"isContinued":false}}\n'


# Add a debug endpoint to see raw request
@app.post("/chat/debug")
async def debug_chat_request(request: Request):
    """Debug endpoint to see raw request data."""
    try:
        body = await request.body()
        print(f"Raw request body: {body.decode()}")
        
        # Try to parse as JSON
        import json
        data = json.loads(body.decode())
        print(f"Parsed JSON: {json.dumps(data, indent=2)}")
        
        return {"status": "ok", "data": data}
    except Exception as e:
        print(f"Error parsing request: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/chat")
async def handle_chat_data(request: AgentRequest, protocol: str = Query("data")):
    """Handle chat requests with agent and computer configuration."""

    print("Received chat request")
    print(f"Request: {request}")
    print(f"Protocol: {protocol}")
    print(f"Messages count: {len(request.messages)}")
    print(f"Agent config: {request.agent}")
    print(f"Computer config: {request.computer}")

    try:
        # Get or create computer instance
        computer = await get_or_create_computer(request.computer)
        
        # Get or create agent instance
        agent = await get_or_create_agent(request.agent, request.computer)
        
        # Calculate agent hash for screenshot queue
        computer_hash = get_computer_hash(request.computer)
        agent_hash = get_agent_hash(request.agent, computer_hash)
        
        # Get the last user message
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        last_message = request.messages[-1]
        if last_message.role != "user":
            raise HTTPException(status_code=400, detail="Last message must be from user")
        
        print(f"Processing message: {last_message.content}")
        
        # Stream response from agent
        response = StreamingResponse(
            stream_agent_response(agent, last_message.content, agent_hash),
            media_type="text/plain"
        )
        response.headers["x-vercel-ai-data-stream"] = "v1"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        return response
        
    except Exception as e:
        print(f"Error in handle_chat_data: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.get("/model")
def handle_model_pull():
    print("Hello from FastAPI handle_model_pull")
    return {"message": "Hello from FastAPI"}


@app.get("/tags")
def get_tags():
    print("Hello from FastAPI get_tags")
    return {"message": "Hello from FastAPI"}


@app.post("/screenshot")
async def take_screenshot(request: ComputerConfig):
    """Take a screenshot of a computer instance."""
    if Computer is None:
        raise HTTPException(status_code=500, detail="Computer library not available")
    
    print(f"Request: {request}")

    try:
        # Map provider to Computer constructor parameters
        computer = None
        
        if request.provider == "host-computer":
            # Host computer configuration
            os_type_map = {
                "linux": "linux",
                "windows": "windows", 
                "macos": "macos"
            }
            os_type = os_type_map.get(request.os, "linux")
            
            computer = Computer(
                use_host_computer_server=True,
                os_type=os_type, # type: ignore[literal-mismatch]
                verbosity=logging.INFO
            )
            
        elif request.provider == "windows-sandbox":
            computer = Computer(
                provider_type=VMProviderType.WINSANDBOX,
                os_type="windows",
                verbosity=logging.INFO
            )
            
        elif request.provider == "lume":
            os_type_map = {
                "macos": "macos",
                "linux": "linux",
                "ubuntu": "linux"
            }
            os_type = os_type_map.get(request.os, "macos")
            
            computer = Computer(
                provider_type=VMProviderType.LUME,
                os_type=os_type, # type: ignore[literal-mismatch]
                name=request.name,
                verbosity=logging.INFO
            )
            
        elif request.provider == "cua-cloud":
            computer = Computer(
                provider_type=VMProviderType.CLOUD,
                os_type="linux",  # CUA cloud typically uses Linux
                name=request.name,
                verbosity=logging.INFO,
                api_key=request.api_key,
            )
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")
        
        if computer is None:
            raise HTTPException(status_code=500, detail="Failed to create computer instance")
        
        # Connect, take screenshot, and disconnect
        await computer.run()
        screenshot_bytes = await computer.interface.screenshot()
        await computer.disconnect()
        
        # Convert screenshot to base64 for JSON response
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        return {
            "success": True,
            "screenshot": screenshot_base64,
            "provider": request.provider,
            "name": request.name,
            "os": request.os
        }
        
    except Exception as e:
        # Make sure to disconnect if something goes wrong
        if 'computer' in locals() and computer is not None:
            try:
                await computer.disconnect()
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Screenshot failed: {str(e)}")


# @app.get("/")
# def read_root():
#     print("Hello from FastAPI")
#     return {"message": "Hello from FastAPI"}
