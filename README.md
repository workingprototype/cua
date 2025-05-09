<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" alt="Cua logo" height="150" srcset="img/logo_white.png">
    <source media="(prefers-color-scheme: light)" alt="Cua logo" height="150" srcset="img/logo_black.png">
    <img alt="Cua logo" height="150" src="img/logo_black.png">
  </picture>

  [![Python](https://img.shields.io/badge/Python-333333?logo=python&logoColor=white&labelColor=333333)](#)
  [![Swift](https://img.shields.io/badge/Swift-F05138?logo=swift&logoColor=white)](#)
  [![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=F0F0F0)](#)
  [![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?&logo=discord&logoColor=white)](https://discord.com/invite/mVnXXpdE85)
</div>

**c/ua** (pronounced "koo-ah") enables AI agents to control full operating systems in high-performance virtual containers with near-native speed on Apple Silicon.

<div align="center">
<video src="https://github.com/user-attachments/assets/06e1974f-8f73-477d-b18a-715d83148e45" width="800" controls></video></div>

# 🚀 Quick Start

Get started with a Computer-Use Agent UI and a VM with a single command:


```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/scripts/playground.sh)"
```


This script will:
- Install Lume CLI for VM management
- Pull the latest macOS CUA image
- Set up Python environment and install required packages
- Create a desktop shortcut for easy access
- Launch the Computer-Use Agent UI

### System Requirements

- Mac with Apple Silicon (M1/M2/M3/M4 series)
- macOS 15 (Sequoia) or newer
- Disk space for VM images (30GB+ recommended)


# 💻 For Developers

### Step 1: Install Lume CLI

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/lume/scripts/install.sh)"
```

Lume CLI manages high-performance macOS/Linux VMs with near-native speed on Apple Silicon.

### Step 2: Pull the macOS CUA Image

```bash
lume pull macos-sequoia-cua:latest
```

The macOS CUA image contains the default Mac apps and the Computer Server for easy automation.

### Step 3: Install Python SDK

```bash
pip install cua-computer "cua-agent[all]"
```

Alternatively, see the [Developer Guide](./docs/Developer-Guide.md) for building from source.

### Step 4: Use in Your Code

```python
# Example: Using the Computer-Use Agent
from agent import ComputerAgent

# Create and run an agent locally using UI-TARS and MLX
agent = ComputerAgent(computer=my_computer, loop="UITARS")
await agent.run("Search for information about CUA on GitHub")

# Example: Direct control of a macOS VM with Computer
from computer import Computer

async with Computer(os_type="macos") as computer:
    # Take a screenshot
    screenshot = await computer.screenshot()
    # Click on an element
    await computer.mouse.click(x=100, y=200)
    # Type text
    await computer.keyboard.type("Hello, world!")
```

For ready-to-use examples, check out our [Notebooks](./notebooks/) collection.

### Lume CLI Reference

```bash
# Install Lume CLI
curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/lume/scripts/install.sh | bash

# List available VM images
lume list

# Pull a VM image
lume pull macos-sequoia-cua:latest

# Create a new VM
lume create my-vm --image macos-sequoia-cua:latest

# Start a VM
lume start my-vm

# Stop a VM
lume stop my-vm

# Delete a VM
lume delete my-vm
```

## Resources

- [When and how to use OpenAI Computer-Use, Anthropic, OmniParser, or UI-TARS for your Computer-Use Agent](./libs/agent/README.md)
- [How to use Lume CLI for managing desktops](./libs/lume/README.md)
- [Training Computer-Use Models: Collecting Human Trajectories with C/ua (Part 1)](https://www.trycua.com/blog/training-computer-use-models-trajectories-1)
- [Build Your Own Operator on macOS (Part 1)](https://www.trycua.com/blog/build-your-own-operator-on-macos-1)

## Modules

| Module | Description | Installation |
|--------|-------------|---------------|
| [**Lume**](./libs/lume/README.md) | VM management for macOS/Linux using Apple's Virtualization.Framework | `curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/lume/scripts/install.sh \| bash` |
| [**Computer**](./libs/computer/README.md) | Interface for controlling virtual machines | `pip install cua-computer` |
| [**Agent**](./libs/agent/README.md) | AI agent framework for automating tasks | `pip install cua-agent` |
| [**SOM**](./libs/som/README.md) | Self-of-Mark library for Agent | `pip install cua-som` |
| [**PyLume**](./libs/pylume/README.md) | Python bindings for Lume | `pip install pylume` |
| [**Computer Server**](./libs/computer-server/README.md) | Server component for Computer | `pip install cua-computer-server` |
| [**Core**](./libs/core/README.md) | Core utilities | `pip install cua-core` |

## Demos

Check out these demos of the Computer-Use Agent in action:

<details open>
<summary><b>MCP Server: Work with Claude Desktop and Tableau</b></summary>
<br>
<div align="center">
    <video src="https://github.com/user-attachments/assets/9f573547-5149-493e-9a72-396f3cff29df" width="800" controls></video>
</div>
</details>

<details>
<summary><b>AI-Gradio: Multi-app workflow with browser, VS Code and terminal</b></summary>
<br>
<div align="center">
    <video src="https://github.com/user-attachments/assets/723a115d-1a07-4c8e-b517-88fbdf53ed0f" width="800" controls></video>
</div>
</details>

## Community

Join our [Discord community](https://discord.com/invite/mVnXXpdE85) to discuss ideas, get assistance, or share your demos!

## License

Cua is open-sourced under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

We welcome contributions to CUA! Please refer to our [Contributing Guidelines](CONTRIBUTING.md) for details.

## Trademarks

Apple, macOS, and Apple Silicon are trademarks of Apple Inc. This project is not affiliated with, endorsed by, or sponsored by Apple Inc.

## Stargazers

Thank you to all our supporters!

[![Stargazers over time](https://starchart.cc/trycua/cua.svg?variant=adaptive)](https://starchart.cc/trycua/cua)

## Contributors

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/f-trycua"><img src="https://avatars.githubusercontent.com/u/195596869?v=4?s=100" width="100px;" alt="f-trycua"/><br /><sub><b>f-trycua</b></sub></a><br /><a href="#code-f-trycua" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://pepicrft.me"><img src="https://avatars.githubusercontent.com/u/663605?v=4?s=100" width="100px;" alt="Pedro Piñera Buendía"/><br /><sub><b>Pedro Piñera Buendía</b></sub></a><br /><a href="#code-pepicrft" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://iamit.in"><img src="https://avatars.githubusercontent.com/u/5647941?v=4?s=100" width="100px;" alt="Amit Kumar"/><br /><sub><b>Amit Kumar</b></sub></a><br /><a href="#code-aktech" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://productsway.com/"><img src="https://avatars.githubusercontent.com/u/870029?v=4?s=100" width="100px;" alt="Dung Duc Huynh (Kaka)"/><br /><sub><b>Dung Duc Huynh (Kaka)</b></sub></a><br /><a href="#code-jellydn" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://zaydkrunz.com"><img src="https://avatars.githubusercontent.com/u/70227235?v=4?s=100" width="100px;" alt="Zayd Krunz"/><br /><sub><b>Zayd Krunz</b></sub></a><br /><a href="#code-ShrootBuck" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/PrashantRaj18198"><img src="https://avatars.githubusercontent.com/u/23168997?v=4?s=100" width="100px;" alt="Prashant Raj"/><br /><sub><b>Prashant Raj</b></sub></a><br /><a href="#code-PrashantRaj18198" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.mobile.dev"><img src="https://avatars.githubusercontent.com/u/847683?v=4?s=100" width="100px;" alt="Leland Takamine"/><br /><sub><b>Leland Takamine</b></sub></a><br /><a href="#code-Leland-Takamine" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ddupont808"><img src="https://avatars.githubusercontent.com/u/3820588?v=4?s=100" width="100px;" alt="ddupont"/><br /><sub><b>ddupont</b></sub></a><br /><a href="#code-ddupont808" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Lizzard1123"><img src="https://avatars.githubusercontent.com/u/46036335?v=4?s=100" width="100px;" alt="Ethan Gutierrez"/><br /><sub><b>Ethan Gutierrez</b></sub></a><br /><a href="#code-Lizzard1123" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://ricterz.me"><img src="https://avatars.githubusercontent.com/u/5282759?v=4?s=100" width="100px;" alt="Ricter Zheng"/><br /><sub><b>Ricter Zheng</b></sub></a><br /><a href="#code-RicterZ" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.trytruffle.ai/"><img src="https://avatars.githubusercontent.com/u/50844303?v=4?s=100" width="100px;" alt="Rahul Karajgikar"/><br /><sub><b>Rahul Karajgikar</b></sub></a><br /><a href="#code-rahulkarajgikar" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/trospix"><img src="https://avatars.githubusercontent.com/u/81363696?v=4?s=100" width="100px;" alt="trospix"/><br /><sub><b>trospix</b></sub></a><br /><a href="#code-trospix" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://wavee.world/invitation/b96d00e6-b802-4a1b-8a66-2e3854a01ffd"><img src="https://avatars.githubusercontent.com/u/22633385?v=4?s=100" width="100px;" alt="Ikko Eltociear Ashimine"/><br /><sub><b>Ikko Eltociear Ashimine</b></sub></a><br /><a href="#code-eltociear" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/dp221125"><img src="https://avatars.githubusercontent.com/u/10572119?v=4?s=100" width="100px;" alt="한석호(MilKyo)"/><br /><sub><b>한석호(MilKyo)</b></sub></a><br /><a href="#code-dp221125" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://www.encona.com/"><img src="https://avatars.githubusercontent.com/u/891558?v=4?s=100" width="100px;" alt="Rahim Nathwani"/><br /><sub><b>Rahim Nathwani</b></sub></a><br /><a href="#code-rahimnathwani" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://mjspeck.github.io/"><img src="https://avatars.githubusercontent.com/u/20689127?v=4?s=100" width="100px;" alt="Matt Speck"/><br /><sub><b>Matt Speck</b></sub></a><br /><a href="#code-mjspeck" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/FinnBorge"><img src="https://avatars.githubusercontent.com/u/9272726?v=4?s=100" width="100px;" alt="FinnBorge"/><br /><sub><b>FinnBorge</b></sub></a><br /><a href="#code-FinnBorge" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->
