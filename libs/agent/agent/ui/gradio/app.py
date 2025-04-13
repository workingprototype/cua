"""
Advanced Gradio UI for Computer-Use Agent

This is a Gradio interface for the Computer-Use Agent
with an advanced UI for model selection and configuration.

Supported Agent Loops and Models:
- AgentLoop.OPENAI: Uses OpenAI Operator CUA model
  • computer_use_preview

- AgentLoop.ANTHROPIC: Uses Anthropic Computer-Use models
  • claude-3-5-sonnet-20240620
  • claude-3-7-sonnet-20250219

- AgentLoop.OMNI (experimental): Uses OmniParser for element pixel-detection
  • claude-3-5-sonnet-20240620
  • claude-3-7-sonnet-20250219
  • gpt-4.5-preview
  • gpt-4o
  • gpt-4

Requirements:
    - Mac with Apple Silicon (M1/M2/M3/M4)
    - macOS 14 (Sonoma) or newer
    - Python 3.10+
    - Lume CLI installed (https://github.com/trycua/cua)
    - OpenAI or Anthropic API key
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, AsyncGenerator, Any, Tuple, Union
import gradio as gr

# Import from agent package
from agent.core.types import AgentResponse
from agent.core.callbacks import DefaultCallbackHandler
from agent.providers.omni.parser import ParseResult
from computer import Computer

from agent import ComputerAgent, AgentLoop, LLM, LLMProvider

# Global variables
global_agent = None
global_computer = None

# Custom Screenshot Handler for Gradio chat
class GradioChatScreenshotHandler(DefaultCallbackHandler):
    """Custom handler that adds screenshots to the Gradio chatbot and updates annotated image."""
    
    def __init__(self, chatbot_history: List[gr.ChatMessage]):
        """Initialize with reference to chat history and annotated image component.
        
        Args:
            chatbot_history: Reference to the Gradio chatbot history list
            annotated_image: Reference to the annotated image component
        """
        self.chatbot_history = chatbot_history
        self.latest_image = None
        self.latest_annotations = []
        logging.info("GradioChatScreenshotHandler initialized with chat history and annotated image")
        print("GradioChatScreenshotHandler initialized")
        
    async def on_screenshot(self, screenshot_base64: str, action_type: str = "", parsed_screen: Optional[ParseResult] = None) -> None:
        """Add screenshot to chatbot when a screenshot is taken and update the annotated image.
        
        Args:
            screenshot_base64: Base64 encoded screenshot
            action_type: Type of action that triggered the screenshot
            
        Returns:
            Original screenshot (does not modify it)
        """
        # Create a markdown image element for the screenshot
        image_markdown = f"![Screenshot after {action_type}](data:image/png;base64,{screenshot_base64})"
        
        # Simply append the screenshot as a new message
        if self.chatbot_history is not None:
            self.chatbot_history.append(gr.ChatMessage(role="assistant", content=image_markdown))

# Map model names to specific provider model names
MODEL_MAPPINGS = {
    "openai": {
        # Default to operator CUA model
        "default": "computer_use_preview",
        # Map standard OpenAI model names to CUA-specific model names
        "gpt-4-turbo": "computer_use_preview",
        "gpt-4o": "computer_use_preview",
        "gpt-4": "computer_use_preview",
        "gpt-4.5-preview": "computer_use_preview",
    },
    "anthropic": {
        # Default to newest model
        "default": "claude-3-7-sonnet-20250219",
        # Specific Claude models for CUA
        "claude-3-5-sonnet-20240620": "claude-3-5-sonnet-20240620",
        "claude-3-7-sonnet-20250219": "claude-3-7-sonnet-20250219",
        # Map standard model names to CUA-specific model names
        "claude-3-opus": "claude-3-7-sonnet-20250219",
        "claude-3-sonnet": "claude-3-5-sonnet-20240620",
        "claude-3-5-sonnet": "claude-3-5-sonnet-20240620",
        "claude-3-7-sonnet": "claude-3-7-sonnet-20250219",
    },
    "omni": {
        # OMNI works with any of these models
        "default": "gpt-4o",
        "gpt-4o": "gpt-4o",
        "gpt-4": "gpt-4",
        "gpt-4.5-preview": "gpt-4.5-preview",
        "claude-3-5-sonnet-20240620": "claude-3-5-sonnet-20240620",
        "claude-3-7-sonnet-20250219": "claude-3-7-sonnet-20250219",
    },
    "ollama": {
        # For Ollama models, we keep the original name
        "default": "llama3",  # A common default model
        # Don't map other models - we'll use the original name
    },
    "oaicompat": {
        # Default for OpenAI-compatible providers like VLLM
        "default": "Qwen2.5-VL-7B-Instruct",
    },
}


def get_provider_and_model(model_name: str, loop_provider: str) -> tuple:
    """
    Determine the provider and actual model name to use based on the input.

    Args:
        model_name: The requested model name
        loop_provider: The requested agent loop provider

    Returns:
        tuple: (provider, model_name_to_use, agent_loop)
    """
    # Get the agent loop
    loop_provider_map = {
        "OPENAI": AgentLoop.OPENAI,
        "ANTHROPIC": AgentLoop.ANTHROPIC,
        "OMNI": AgentLoop.OMNI,
        "OMNI-OLLAMA": AgentLoop.OMNI,  # Special case for Ollama models with OMNI parser
    }
    agent_loop = loop_provider_map.get(loop_provider, AgentLoop.OPENAI)

    # Set up the provider and model based on the loop and model_name
    if agent_loop == AgentLoop.OPENAI:
        provider = LLMProvider.OPENAI
        model_name_to_use = MODEL_MAPPINGS["openai"].get(
            model_name.lower(), MODEL_MAPPINGS["openai"]["default"]
        )
    elif agent_loop == AgentLoop.ANTHROPIC:
        provider = LLMProvider.ANTHROPIC
        model_name_to_use = MODEL_MAPPINGS["anthropic"].get(
            model_name.lower(), MODEL_MAPPINGS["anthropic"]["default"]
        )
    elif agent_loop == AgentLoop.OMNI:
        # For OMNI, select provider based on model name or loop_provider
        if loop_provider == "OMNI-OLLAMA":
            provider = LLMProvider.OLLAMA

            # For Ollama models from the UI dropdown, we use the model name as is
            # No need to parse it - it's already the correct Ollama model name
            model_name_to_use = model_name
        elif "claude" in model_name.lower():
            provider = LLMProvider.ANTHROPIC
            model_name_to_use = MODEL_MAPPINGS["omni"].get(
                model_name.lower(), MODEL_MAPPINGS["omni"]["default"]
            )
        elif "gpt" in model_name.lower():
            provider = LLMProvider.OPENAI
            model_name_to_use = MODEL_MAPPINGS["omni"].get(
                model_name.lower(), MODEL_MAPPINGS["omni"]["default"]
            )
        else:
            # Handle custom model names - use the OAICOMPAT provider
            provider = LLMProvider.OAICOMPAT
            # Use the model name as is without mapping, or use default if empty
            model_name_to_use = (
                model_name if model_name.strip() else MODEL_MAPPINGS["oaicompat"]["default"]
            )
    else:
        # Default to OpenAI if unrecognized loop
        provider = LLMProvider.OPENAI
        model_name_to_use = MODEL_MAPPINGS["openai"]["default"]
        agent_loop = AgentLoop.OPENAI

    return provider, model_name_to_use, agent_loop


def get_ollama_models() -> List[str]:
    """Get available models from Ollama if installed."""
    try:
        import subprocess

        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) < 2:  # No models or just header
                return []

            models = []
            # Skip header line
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    model_name = parts[0]
                    models.append(f"OMNI: Ollama {model_name}")
            return models
        return []
    except Exception as e:
        logging.error(f"Error getting Ollama models: {e}")
        return []


def extract_synthesized_text(result: Union[AgentResponse, Dict[str, Any]]) -> str:
    """Extract synthesized text from the agent result."""
    synthesized_text = ""

    if "output" in result and result["output"]:
        for output in result["output"]:
            if output.get("type") == "reasoning":
                content = output.get("content", "")
                if content:
                    synthesized_text += f"{content}\n"

            elif output.get("type") == "message":
                # Handle message type outputs - can contain rich content
                content = output.get("content", [])

                # Content is usually an array of content blocks
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "output_text":
                            text_value = block.get("text", "")
                            if text_value:
                                synthesized_text += f"{text_value}\n"

            elif output.get("type") == "computer_call":
                action = output.get("action", {})
                action_type = action.get("type", "")

                # Create a descriptive text about the action
                if action_type == "click":
                    button = action.get("button", "")
                    x = action.get("x", "")
                    y = action.get("y", "")
                    synthesized_text += f"Clicked {button} at position ({x}, {y}).\n"
                elif action_type == "type":
                    text = action.get("text", "")
                    synthesized_text += f"Typed: {text}.\n"
                elif action_type == "keypress":
                    # Extract key correctly from either keys array or key field
                    if isinstance(action.get("keys"), list):
                        key = ", ".join(action.get("keys"))
                    else:
                        key = action.get("key", "")

                    synthesized_text += f"Pressed key: {key}\n"
                else:
                    synthesized_text += f"Performed {action_type} action.\n"

    return synthesized_text.strip()


def create_computer_instance(verbosity: int = logging.INFO) -> Computer:
    """Create or get the global Computer instance."""
    global global_computer

    if global_computer is None:
        global_computer = Computer(verbosity=verbosity)

    return global_computer


def create_agent(
    provider: LLMProvider,
    agent_loop: AgentLoop,
    model_name: str,
    api_key: Optional[str] = None,
    save_trajectory: bool = True,
    only_n_most_recent_images: int = 3,
    verbosity: int = logging.INFO,
    use_ollama: bool = False,
    use_oaicompat: bool = False,
    provider_base_url: Optional[str] = None,
) -> ComputerAgent:
    """Create or update the global agent with the specified parameters."""
    global global_agent

    # Create the computer if not already done
    computer = create_computer_instance(verbosity=verbosity)

    # Extra configuration to pass to the agent
    extra_config = {}

    # For Ollama models, we'll pass use_ollama and the model_name directly
    if use_ollama:
        extra_config["use_ollama"] = True
        extra_config["ollama_model"] = model_name
        print(f"DEBUG - Using Ollama with model: {model_name}")

    # Get API key from environment if not provided
    if api_key is None:
        if provider == LLMProvider.OPENAI:
            api_key = os.environ.get("OPENAI_API_KEY", "")
        elif provider == LLMProvider.ANTHROPIC:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # Use provided provider_base_url if available, otherwise use default
    default_base_url = "http://localhost:1234/v1" if use_oaicompat else None
    custom_base_url = provider_base_url or default_base_url

    if use_oaicompat:
        # Special handling for OAICOMPAT - use OAICOMPAT provider with custom base URL
        print(
            f"DEBUG - Creating OAICOMPAT agent with model: {model_name}, URL: {custom_base_url}"
        )
        llm = LLM(
            provider=LLMProvider.OAICOMPAT,  # Set to OAICOMPAT instead of using original provider
            name=model_name,
            provider_base_url=custom_base_url,
        )
        print(f"DEBUG - LLM provider is now: {llm.provider}, base URL: {llm.provider_base_url}")
        # Note: Don't pass use_oaicompat to the agent, as it doesn't accept this parameter
    elif provider == LLMProvider.OAICOMPAT:
        # This path is unlikely to be taken with our current approach
        llm = LLM(provider=provider, name=model_name, provider_base_url=custom_base_url)
    else:
        # For other providers, just use standard parameters
        llm = LLM(provider=provider, name=model_name)

    # Create or update the agent
    global_agent = ComputerAgent(
        computer=computer,
        loop=agent_loop,
        model=llm,
        api_key=api_key,
        save_trajectory=save_trajectory,
        only_n_most_recent_images=only_n_most_recent_images,
        verbosity=verbosity,
        **extra_config,
    )

    return global_agent


def process_agent_result(result: Union[AgentResponse, Dict[str, Any]]) -> str:
    """Process agent results for the Gradio UI."""
    # Extract text content
    text_obj = result.get("text", {})

    # For OpenAI's Computer-Use Agent, text field is an object with format property
    if (
        text_obj
        and isinstance(text_obj, dict)
        and "format" in text_obj
        and not text_obj.get("value", "")
    ):
        content = extract_synthesized_text(result)
    else:
        # For other types of results, try to get text directly
        if isinstance(text_obj, dict):
            if "value" in text_obj:
                content = text_obj["value"]
            elif "text" in text_obj:
                content = text_obj["text"]
            elif "content" in text_obj:
                content = text_obj["content"]
            else:
                content = ""
        else:
            content = str(text_obj) if text_obj else ""

    # If still no content but we have outputs, create a summary
    if not content and "output" in result and result["output"]:
        output = result["output"]
        for out in output:
            if out.get("type") == "reasoning":
                content = out.get("content", "")
                if content:
                    break
            elif out.get("type") == "computer_call":
                action = out.get("action", {})
                action_type = action.get("type", "")
                if action_type:
                    content = f"Performing action: {action_type}"
                    break

    # Clean up the text - ensure content is a string
    if not isinstance(content, str):
        content = str(content) if content else ""

    return content

def create_gradio_ui(
    provider_name: str = "openai",
    model_name: str = "gpt-4o",
) -> gr.Blocks:
    """Create a Gradio UI for the Computer-Use Agent.

    Args:
        provider_name: The provider to use (e.g., "openai", "anthropic")
        model_name: The model to use (e.g., "gpt-4o", "claude-3-7-sonnet")

    Returns:
        A Gradio Blocks application
    """
    # Check for API keys
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # Prepare model choices based on available API keys
    openai_models = []
    anthropic_models = []
    omni_models = []

    if openai_api_key:
        openai_models = ["OpenAI: Computer-Use Preview"]
        omni_models += [
            "OMNI: OpenAI GPT-4o",
            "OMNI: OpenAI GPT-4.5-preview",
        ]

    if anthropic_api_key:
        anthropic_models = [
            "Anthropic: Claude 3.7 Sonnet (20250219)",
            "Anthropic: Claude 3.5 Sonnet (20240620)",
        ]
        omni_models += ["OMNI: Claude 3.7 Sonnet (20250219)", "OMNI: Claude 3.5 Sonnet (20240620)"]

    # Get Ollama models for OMNI
    ollama_models = get_ollama_models()
    if ollama_models:
        omni_models += ollama_models

    # Format model choices
    provider_to_models = {
        "OPENAI": openai_models,
        "ANTHROPIC": anthropic_models,
        "OMNI": omni_models + ["Custom model..."],  # Add custom model option
    }

    # Get initial agent loop and model based on provided parameters
    if provider_name.lower() == "openai":
        initial_loop = "OPENAI"
        initial_model = "OpenAI: Computer-Use Preview" if openai_models else "No models available"
    elif provider_name.lower() == "anthropic":
        initial_loop = "ANTHROPIC"
        initial_model = anthropic_models[0] if anthropic_models else "No models available"
    else:
        initial_loop = "OMNI"
        if model_name == "gpt-4o" and "OMNI: OpenAI GPT-4o" in omni_models:
            initial_model = "OMNI: OpenAI GPT-4o"
        elif "claude" in model_name.lower() and omni_models:
            initial_model = next((m for m in omni_models if "Claude" in m), omni_models[0])
        else:
            initial_model = omni_models[0] if omni_models else "No models available"

    # Example prompts
    example_messages = [
        "Create a Python virtual environment, install pandas and matplotlib, then plot stock data",
        "Open a PDF in Preview, add annotations, and save it as a compressed version",
        "Open Safari, search for 'macOS automation tools', and save the first three results as bookmarks",
        "Configure SSH keys and set up a connection to a remote server",
    ]

    # Function to update model choices based on agent loop selection
    def update_model_choices(loop):
        models = provider_to_models.get(loop, [])
        if loop == "OMNI":
            # For OMNI, include the custom model option
            if not models:
                models = ["Custom model..."]
            elif "Custom model..." not in models:
                models.append("Custom model...")

            return gr.update(
                choices=models, value=models[0] if models else "Custom model...", interactive=True
            )
        else:
            # For other providers, use standard dropdown without custom option
            if not models:
                return gr.update(
                    choices=["No models available"], value="No models available", interactive=True
                )
            return gr.update(choices=models, value=models[0] if models else None, interactive=True)

    # Create the Gradio interface with advanced UI
    with gr.Blocks(title="Computer-Use Agent") as demo:
        with gr.Row():
            # Left column for settings
            with gr.Column(scale=1):
                # Logo with theme-aware styling
                gr.HTML(
                    """
                    <style>
                    .light-logo, .dark-logo {
                        display: block;
                        margin: 0 auto;
                        width: 80px;
                    }
                    /* Hide dark logo in light mode */
                    .dark-logo {
                        display: none;
                    }
                    /* In dark mode, hide light logo and show dark logo */
                    .dark .light-logo {
                        display: none;
                    }
                    .dark .dark-logo {
                        display: block;
                    }
                    </style>
                    <div style="display: flex; justify-content: center; margin-bottom: 0.5em">
                        <img class="light-logo" alt="CUA Logo" 
                             src="https://github.com/trycua/cua/blob/main/img/logo_black.png?raw=true" />
                        <img class="dark-logo" alt="CUA Logo" 
                             src="https://github.com/trycua/cua/blob/main/img/logo_white.png?raw=true" />
                    </div>
                    """
                )

                # Add installation prerequisites as a collapsible section
                with gr.Accordion("Prerequisites & Installation", open=False):
                    gr.Markdown(
                        """
                    ## Prerequisites
                    
                    Before using the Computer-Use Agent, you need to set up the Lume daemon and pull the macOS VM image.
                    
                    ### 1. Install Lume daemon
                    
                    While a lume binary is included with Computer, we recommend installing the standalone version with brew, and starting the lume daemon service:
                    
                    ```bash
                    sudo /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/lume/scripts/install.sh)"
                    ```
                    
                    ### 2. Start the Lume daemon service
                    
                    In a separate terminal:
                    
                    ```bash
                    lume serve
                    ```
                    
                    ### 3. Pull the pre-built macOS image
                    
                    ```bash
                    lume pull macos-sequoia-cua:latest --no-cache
                    ```
                    
                    Initial download requires 80GB storage, but reduces to ~30GB after first run due to macOS's sparse file system.
                    
                    VMs are stored in `~/.lume`, and locally cached images are stored in `~/.lume/cache`.
                    
                    ### 4. Test the sandbox
                    
                    ```bash
                    lume run macos-sequoia-cua:latest
                    ```
                    
                    For more detailed instructions, visit the [CUA GitHub repository](https://github.com/trycua/cua).
                    """
                    )

                with gr.Accordion("Configuration", open=False):
                    # Configuration options
                    agent_loop = gr.Dropdown(
                        choices=["OPENAI", "ANTHROPIC", "OMNI"],
                        label="Agent Loop",
                        value=initial_loop,
                        info="Select the agent loop provider",
                    )

                    # Create model selection dropdown with custom value support for OMNI
                    model_choice = gr.Dropdown(
                        choices=provider_to_models.get(initial_loop, ["No models available"]),
                        label="LLM Provider and Model",
                        value=initial_model,
                        info="Select model or choose 'Custom model...' to enter a custom name",
                        interactive=True,
                    )

                    # Add custom model textbox (only visible when "Custom model..." is selected)
                    custom_model = gr.Textbox(
                        label="Custom Model Name",
                        placeholder="Enter custom model name (e.g., Qwen2.5-VL-7B-Instruct)",
                        value="Qwen2.5-VL-7B-Instruct",  # Default value
                        visible=False,  # Initially hidden
                        interactive=True,
                    )
                    
                    # Add custom provider base URL textbox (only visible when "Custom model..." is selected)
                    provider_base_url = gr.Textbox(
                        label="Provider Base URL",
                        placeholder="Enter provider base URL (e.g., http://localhost:1234/v1)",
                        value="http://localhost:1234/v1",  # Default value
                        visible=False,  # Initially hidden
                        interactive=True,
                    )
                    
                    # Add custom API key textbox (only visible when "Custom model..." is selected)
                    provider_api_key = gr.Textbox(
                        label="Provider API Key",
                        placeholder="Enter provider API key (if required)",
                        value="",  # Default empty value
                        visible=False,  # Initially hidden
                        interactive=True,
                        type="password",  # Hide the API key
                    )

                    save_trajectory = gr.Checkbox(
                        label="Save Trajectory",
                        value=True,
                        info="Save the agent's trajectory for debugging",
                        interactive=True,
                    )

                    recent_images = gr.Slider(
                        label="Recent Images",
                        minimum=1,
                        maximum=10,
                        value=3,
                        step=1,
                        info="Number of recent images to keep in context",
                        interactive=True,
                    )

            # Right column for chat interface
            with gr.Column(scale=2):
                # Add instruction text before the chat interface
                gr.Markdown(
                    "Ask me to perform tasks in a virtual macOS environment.<br>Built with <a href='https://github.com/trycua/cua' target='_blank'>github.com/trycua/cua</a>."
                )

                chatbot_history = gr.Chatbot(type='messages')
                msg = gr.Textbox(
                    placeholder="Ask me to perform tasks in a virtual macOS environment"
                )
                clear = gr.Button("Clear")

                # Add examples
                example_group = gr.Examples(examples=example_messages, inputs=msg)

                # Function to handle chat submission
                def chat_submit(message, history):
                    # Add user message to history
                    history.append(gr.ChatMessage(role="user", content=message))
                    return "", history

                # Function to process agent response after user input
                def process_response(
                    history,
                    model_choice_value,
                    custom_model_value,
                    agent_loop_choice,
                    save_traj,
                    recent_imgs,
                    custom_url_value=None,
                    custom_api_key=None,
                ):
                    if not history:
                        yield history
                        return

                    # Get the last user message
                    last_user_message = history[-1]['content']
                    
                    # Use custom model value if "Custom model..." is selected
                    model_to_use = (
                        custom_model_value
                        if model_choice_value == "Custom model..."
                        else model_choice_value
                    )
                    
                    # Create a new async event loop for this function call
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def _stream_agent_responses():
                        try:
                            # Get the model, agent loop, and provider
                            provider, model_name, agent_loop_type = get_provider_and_model(
                                model_to_use, agent_loop_choice
                            )
                            
                            # Special handling for OAICOMPAT
                            is_oaicompat = str(provider) == "oaicompat"
                            
                            # Get API key based on provider
                            if model_choice_value == "Custom model..." and custom_api_key:
                                # Use custom API key if provided for custom model
                                api_key = custom_api_key
                                print(f"DEBUG - Using custom API key for model: {model_name}")
                            elif provider == LLMProvider.OPENAI:
                                api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
                            elif provider == LLMProvider.ANTHROPIC:
                                api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
                            else:
                                api_key = ""
                                
                            # Create or update the agent
                            create_agent(
                                provider=provider,
                                agent_loop=agent_loop_type,
                                model_name=model_name,
                                api_key=api_key,
                                save_trajectory=save_traj,
                                only_n_most_recent_images=recent_imgs,
                                use_ollama=agent_loop_choice == "OMNI-OLLAMA",
                                use_oaicompat=is_oaicompat,
                                provider_base_url=custom_url_value if is_oaicompat and model_choice_value == "Custom model..." else None,
                            )
                            
                            if global_agent is None:
                                # Add initial empty assistant message
                                history.append(gr.ChatMessage(role="assistant", content="Failed to create agent. Check API keys and configuration."))
                                yield history
                                return
                                
                                # Add the screenshot handler to the agent's loop if available
                            if global_agent and hasattr(global_agent, "_loop"):
                                print("DEBUG - Adding screenshot handler to agent loop")
                                
                                # Create the screenshot handler with references to UI components
                                screenshot_handler = GradioChatScreenshotHandler(
                                    history
                                )
                                
                                # Add the handler to the callback manager if it exists
                                if hasattr(global_agent._loop, "callback_manager"):
                                    global_agent._loop.callback_manager.add_handler(screenshot_handler)
                                    print(f"DEBUG - Screenshot handler added to callback manager with history: {id(history)}")
                                    
                            # Stream responses from the agent
                            async for result in global_agent.run(last_user_message):
                                # Process result
                                content = process_agent_result(result)
                                
                                # # Skip empty content
                                if content:
                                    history.append(gr.ChatMessage(role="assistant", content=content))
                                yield history
                                
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            # Update with error message
                            history.append(gr.ChatMessage(role="assistant", content=f"Error: {str(e)}"))
                            yield history
                    
                    # Create an async function to run the generator
                    async def run_generator():
                        async for update in _stream_agent_responses():
                            yield update
                    
                    # Run the wrapper function
                    try:
                        # Create a generator by running the async function
                        generator = run_generator()
                        # Push the first element to start the generator
                        first_item = loop.run_until_complete(generator.__anext__())
                        yield first_item
                        
                        # Keep iterating until StopAsyncIteration
                        while True:
                            try:
                                item = loop.run_until_complete(generator.__anext__())
                                yield item
                            except StopAsyncIteration:
                                break
                    finally:
                        loop.close()

                # Connect the components
                msg.submit(chat_submit, [msg, chatbot_history], [msg, chatbot_history]).then(
                    process_response,
                    [
                        chatbot_history,
                        model_choice,
                        custom_model,
                        agent_loop,
                        save_trajectory,
                        recent_images,
                        provider_base_url,
                        provider_api_key,
                    ],
                    [chatbot_history],
                )

                # Clear button functionality
                clear.click(lambda: None, None, chatbot_history, queue=False)

                # Connect agent_loop changes to model selection
                agent_loop.change(
                    fn=update_model_choices,
                    inputs=[agent_loop],
                    outputs=[model_choice],
                    queue=False,  # Process immediately without queueing
                )

                # Show/hide custom model, provider base URL, and API key textboxes based on dropdown selection
                def update_custom_model_visibility(model_value):
                    is_custom = model_value == "Custom model..."
                    return gr.update(visible=is_custom), gr.update(visible=is_custom), gr.update(visible=is_custom)

                model_choice.change(
                    fn=update_custom_model_visibility,
                    inputs=[model_choice],
                    outputs=[custom_model, provider_base_url, provider_api_key],
                    queue=False,  # Process immediately without queueing
                )

    return demo


def test_cua():
    """Standalone function to launch the Gradio app."""
    demo = create_gradio_ui()
    demo.launch(share=False)  # Don't create a public link


if __name__ == "__main__":
    test_cua()
