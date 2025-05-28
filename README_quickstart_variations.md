# Quick Start Section Variations

Here are 5 different variations for the Quick Start section, focused on users who want to use Computer-Use Agent UI:

## Variation 1: User-Focused with Technical Context

# 🚀 Quick Start

**Launch the Computer-Use Agent UI in 60 seconds.**

## macOS (Local + Cloud)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/scripts/playground.sh)"
```

<details>
<summary>What does this script do?</summary>

The playground script automates the complete setup process:

1. **Install Lume CLI**
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/lume/scripts/install.sh)"
   ```

2. **Pull the macOS CUA image**
   ```bash
   lume pull macos-sequoia-cua:latest
   ```

3. **Run the VM**
   ```bash
   lume run macos-sequoia-cua:latest
   ```

4. **Install Python packages**
   ```bash
   pip install "cua-computer[all]" "cua-agent[all]"
   ```

5. **Launch the UI**
   ```bash
   python -m agent.ui.gradio.app
   ```

You can run these steps manually if you prefer more control over the process.
</details>

## Windows/Linux (Cloud)
```bash
pip install "cua-computer[all]" "cua-agent[all]" ; python -m agent.ui.gradio.app
```

*The Agent UI uses the Computer module to provide secure macOS/Linux desktops via Lume CLI (local) or [C/ua Cloud](https://trycua.com) (cloud), and the Agent module for local/API agents with OpenAI AgentResponse format and [tracing](https://trycua.com/trajectory-viewer).*

---

## Variation 2: Clear User Intent

# 🚀 Quick Start

**Want to use Computer-Use Agents? Get the UI running now.**

### macOS Users
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/scripts/playground.sh)"
```

<details>
<summary>What does this script do?</summary>

1. **Install Lume CLI for VM management**
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/lume/scripts/install.sh)"
   ```

2. **Download the pre-configured macOS image**
   ```bash
   lume pull macos-sequoia-cua:latest
   ```

3. **Start the virtual machine**
   ```bash
   lume run macos-sequoia-cua:latest
   ```

4. **Install the Python SDK**
   ```bash
   pip install "cua-computer[all]" "cua-agent[all]"
   ```

5. **Launch the Computer-Use Agent UI**
   ```bash
   python -m agent.ui.gradio.app
   ```
</details>

### Windows/Linux Users  
```bash
pip install "cua-computer[all]" "cua-agent[all]" ; python -m agent.ui.gradio.app
```

*Technical details: The UI leverages the Computer module (secure desktops via Lume CLI or [C/ua Cloud](https://trycua.com)) and Agent module (local/API agents with OpenAI AgentResponse format and [tracing](https://trycua.com/trajectory-viewer)).*

---

## Variation 3: Direct and Simple

# 🚀 Quick Start

**Get the Computer-Use Agent UI running:**

```bash
# macOS (local + cloud options)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/scripts/playground.sh)"
```

<details>
<summary>What does this script do?</summary>

1. `curl -fsSL .../install.sh | bash` - Install Lume CLI
2. `lume pull macos-sequoia-cua:latest` - Download VM image  
3. `lume run macos-sequoia-cua:latest` - Start VM
4. `pip install "cua-computer[all]" "cua-agent[all]"` - Install packages
5. `python -m agent.ui.gradio.app` - Launch UI
</details>

```bash
# Windows/Linux (cloud containers)
pip install "cua-computer[all]" "cua-agent[all]" ; python -m agent.ui.gradio.app
```

*For developers: Uses Computer module (secure desktops via Lume CLI or [C/ua Cloud](https://trycua.com)) + Agent module (local/API agents with OpenAI AgentResponse and [tracing](https://trycua.com/trajectory-viewer)).*

---

## Variation 4: Problem-Solution

# 🚀 Quick Start

**Need to automate desktop tasks? Launch the Computer-Use Agent UI.**

**macOS:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/scripts/playground.sh)"
```

<details>
<summary>What does this script do?</summary>

Behind the scenes, the playground script runs these commands:

1. **Install Lume CLI**
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/lume/scripts/install.sh)"
   ```

2. **Pull macOS CUA image**
   ```bash
   lume pull macos-sequoia-cua:latest
   ```

3. **Run the virtual machine**
   ```bash
   lume run macos-sequoia-cua:latest
   ```

4. **Install Python dependencies**
   ```bash
   pip install "cua-computer[all]" "cua-agent[all]"
   ```

5. **Start the Agent UI**
   ```bash
   python -m agent.ui.gradio.app
   ```
</details>

**Windows/Linux:**
```bash
pip install "cua-computer[all]" "cua-agent[all]" ; python -m agent.ui.gradio.app
```

*Architecture: Computer module provides secure desktops (Lume CLI locally, [C/ua Cloud](https://trycua.com) remotely), Agent module handles local/API agents with OpenAI AgentResponse format and [tracing](https://trycua.com/trajectory-viewer).*

---

## Variation 5: Ultra Simple

# 🚀 Quick Start

**Start using Computer-Use Agents:**

**macOS:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/scripts/playground.sh)"
```

<details>
<summary>What does this script do?</summary>

1. `lume install` - Install VM management CLI
2. `lume pull macos-sequoia-cua:latest` - Download macOS image
3. `lume run macos-sequoia-cua:latest` - Start VM
4. `pip install "cua-computer[all]" "cua-agent[all]"` - Install packages
5. `python -m agent.ui.gradio.app` - Launch UI
</details>

**Windows/Linux:**
```bash
pip install "cua-computer[all]" "cua-agent[all]" ; python -m agent.ui.gradio.app
```

*Uses Computer module (secure desktops via Lume CLI or [C/ua Cloud](https://trycua.com)) + Agent module (local/API agents with OpenAI AgentResponse and [tracing](https://trycua.com/trajectory-viewer)).*

---

## Recommendation

**Variation 1** is the best choice because:

1. **Clear User Intent**: "Launch the Computer-Use Agent UI" - immediately clear what this does
2. **Time Promise**: "in 60 seconds" sets expectations
3. **Technical Context**: Module details are at the bottom as context, not the focus
4. **User-First**: Focuses on what the user wants to accomplish
5. **Complete**: Still includes all necessary technical information for developers

This puts the user's goal first while keeping the technical architecture details available for those who need them.
