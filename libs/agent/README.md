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

**Agent** is a Computer Use (CUA) framework for running multi-app agentic workflows targeting macOS and Linux sandbox, supporting local (Ollama) and cloud model providers (OpenAI, Anthropic, Groq, DeepSeek, Qwen). The framework integrates with Microsoft's OmniParser for enhanced UI understanding and interaction.

> While our north star is to create a 1-click experience, this preview of Agent might be still a bit rough around the edges. We appreciate your patience as we work to improve the experience.

### Get started with Agent

<div align="center">
    <img src="../../img/agent.png"/>
</div>

## Install

### cua-agent

```bash
pip install "cua-agent[all]"

# or install specific loop providers
pip install "cua-agent[anthropic]"
pip install "cua-agent[omni]"
```

## Run

Refer to these notebooks for step-by-step guides on how to use the Computer-Use Agent (CUA):

- [Agent Notebook](../../notebooks/agent_nb.ipynb) - Complete examples and workflows