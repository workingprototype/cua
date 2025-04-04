<div align="center">
<h1>
  <div class="image-wrapper" style="display: inline-block;">
    <picture>
      <source media="(prefers-color-scheme: dark)" alt="logo" height="150" srcset="../../img/logo_white.png" style="display: block; margin: auto;">
      <source media="(prefers-color-scheme: light)" alt="logo" height="150" srcset="../../img/logo_black.png" style="display: block; margin: auto;">
      <img alt="Shows my svg">
    </picture>
  </div>

  [![Python](https://img.shields.io/badge/Python-333333?logo=python&logoColor=white&labelColor=333333)](#)
  [![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=F0F0F0)](#)
  [![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?&logo=discord&logoColor=white)](https://discord.com/invite/mVnXXpdE85)
  [![PyPI](https://img.shields.io/pypi/v/cua-computer?color=333333)](https://pypi.org/project/cua-computer/)
</h1>
</div>

**cua-agent** is a general Computer-Use framework for running multi-app agentic workflows targeting macOS and Linux sandbox created with Cua, supporting local (Ollama) and cloud model providers (OpenAI, Anthropic, Groq, DeepSeek, Qwen).

### Get started with Agent

<div align="center">
    <img src="../../img/agent.png"/>
</div>

## Install

```bash
pip install "cua-agent[all]"

# or install specific loop providers
pip install "cua-agent[openai]" # OpenAI Cua Loop
pip install "cua-agent[anthropic]" # Anthropic Cua Loop
pip install "cua-agent[omni]" # Cua Loop based on OmniParser (includes Ollama for local models)
```

## Run

```bash
async with Computer() as macos_computer:
  # Create agent with loop and provider
  agent = ComputerAgent(
      computer=macos_computer,
      loop=AgentLoop.OPENAI,
      model=LLM(provider=LLMProvider.OPENAI)
  )

  tasks = [
      "Look for a repository named trycua/cua on GitHub.",
      "Check the open issues, open the most recent one and read it.",
      "Clone the repository in users/lume/projects if it doesn't exist yet.",
      "Open the repository with an app named Cursor (on the dock, black background and white cube icon).",
      "From Cursor, open Composer if not already open.",
      "Focus on the Composer text area, then write and submit a task to help resolve the GitHub issue.",
  ]

  for i, task in enumerate(tasks):
      print(f"\nExecuting task {i}/{len(tasks)}: {task}")
      async for result in agent.run(task):
          print(result)

      print(f"\n✅ Task {i+1}/{len(tasks)} completed: {task}")
```

Refer to these notebooks for step-by-step guides on how to use the Computer-Use Agent (CUA):

- [Agent Notebook](../../notebooks/agent_nb.ipynb) - Complete examples and workflows

## Agent Loops

The `cua-agent` package provides three agent loops variations, based on different CUA models providers and techniques:

| Agent Loop | Supported Models | Description | Set-Of-Marks |
|:-----------|:-----------------|:------------|:-------------|
| `AgentLoop.OPENAI` | • `computer_use_preview` | Use OpenAI Operator CUA model | Not Required |
| `AgentLoop.ANTHROPIC` | • `claude-3-5-sonnet-20240620`<br>• `claude-3-7-sonnet-20250219` | Use Anthropic Computer-Use | Not Required |
| `AgentLoop.OMNI` <br>(experimental) | • `claude-3-5-sonnet-20240620`<br>• `claude-3-7-sonnet-20250219`<br>• `gpt-4.5-preview`<br>• `gpt-4o`<br>• `gpt-4` | Use OmniParser for element pixel-detection (SoM) and any VLMs for UI Grounding and Reasoning | OmniParser |

## AgentResponse
The `AgentResponse` class represents the structured output returned after each agent turn. It contains the agent's response, reasoning, tool usage, and other metadata. The response format aligns with the new [OpenAI Agent SDK specification](https://platform.openai.com/docs/api-reference/responses) for better consistency across different agent loops.

```python
async for result in agent.run(task):
  print("Response ID: ", result.get("id"))

  # Print detailed usage information
  usage = result.get("usage")
  if usage:
      print("\nUsage Details:")
      print(f"  Input Tokens: {usage.get('input_tokens')}")
      if "input_tokens_details" in usage:
          print(f"  Input Tokens Details: {usage.get('input_tokens_details')}")
      print(f"  Output Tokens: {usage.get('output_tokens')}")
      if "output_tokens_details" in usage:
          print(f"  Output Tokens Details: {usage.get('output_tokens_details')}")
      print(f"  Total Tokens: {usage.get('total_tokens')}")

  print("Response Text: ", result.get("text"))

  # Print tools information
  tools = result.get("tools")
  if tools:
      print("\nTools:")
      print(tools)

  # Print reasoning and tool call outputs
  outputs = result.get("output", [])
  for output in outputs:
      output_type = output.get("type")
      if output_type == "reasoning":
          print("\nReasoning Output:")
          print(output)
      elif output_type == "computer_call":
          print("\nTool Call Output:")
          print(output)
```
