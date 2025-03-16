# FAQs

### Why a local sandbox?

A local sandbox is a dedicated environment that is isolated from the rest of the system. As AI agents rapidly evolve towards 70-80% success rates on average tasks, having a controlled and secure environment becomes crucial. Cua's Computer-Use AI agents run in a local sandbox to ensure reliability, safety, and controlled execution.

Benefits of using a local sandbox rather than running the Computer-Use AI agent in the host system:

- **Reliability**: The sandbox provides a reproducible environment - critical for benchmarking and debugging agent behavior. Frameworks like [OSWorld](https://github.com/xlang-ai/OSWorld), [Simular AI](https://github.com/simular-ai/Agent-S), Microsoft's [OmniTool](https://github.com/microsoft/OmniParser/tree/master/omnitool), [WindowsAgentArena](https://github.com/microsoft/WindowsAgentArena) and more are using Computer-Use AI agents running in local sandboxes.
- **Safety & Isolation**: The sandbox is isolated from the rest of the system, protecting sensitive data and system resources. As CUA agent capabilities grow, this isolation becomes increasingly important for preventing potential safety breaches.
- **Control**: The sandbox can be easily monitored and terminated if needed, providing oversight for autonomous agent operation.

### Where are the sandbox images stored?

Sandbox are stored in `~/.lume`, and cached images are stored in `~/.lume/cache`.

### Which image is Computer using?

Computer uses an optimized macOS image for Computer-Use interactions, with pre-installed apps and settings for optimal performance.
The image is available on our [ghcr registry](https://github.com/orgs/trycua/packages/container/package/macos-sequoia-cua).

### Are Sandbox disks taking up all the disk space?

No, macOS uses sparse files, which only allocate space as needed. For example, VM disks totaling 50 GB may only use 20 GB on disk.

### How do I delete a VM?

```bash
lume delete <name>
```

### How do I troubleshoot Computer not connecting to lume daemon?

If you're experiencing connection issues between Computer and the lume daemon, it could be because the port 3000 (used by lume) is already in use by an orphaned process. You can diagnose this issue with:

```bash
sudo lsof -i :3000
```

This command will show all processes using port 3000. If you see a lume process already running, you can terminate it with:

```bash
kill <PID>
```

Where `<PID>` is the process ID shown in the output of the `lsof` command. After terminating the process, run `lume serve` again to start the lume daemon.

### What information does Cua track?

Cua tracks anonymized usage and error report statistics; we ascribe to Posthog's approach as detailed [here](https://posthog.com/blog/open-source-telemetry-ethical). If you would like to opt out of sending anonymized info, you can set `telemetry_enabled` to false in the Computer or Agent constructor. Check out our [Telemetry](Telemetry.md) documentation for more details.
