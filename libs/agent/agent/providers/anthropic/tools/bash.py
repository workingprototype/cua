import asyncio
import os
from typing import ClassVar, Literal, Dict, Any
from computer.computer import Computer

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult
from ....core.tools.bash import BaseBashTool


class _BashSession:
    """A session of a bash shell."""

    _started: bool
    _process: asyncio.subprocess.Process

    command: str = "/bin/bash"
    _output_delay: float = 0.2  # seconds
    _timeout: float = 120.0  # seconds
    _sentinel: str = "<<exit>>"

    def __init__(self):
        self._started = False
        self._timed_out = False

    async def start(self):
        if self._started:
            return

        self._process = await asyncio.create_subprocess_shell(
            self.command,
            preexec_fn=os.setsid,
            shell=True,
            bufsize=0,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        self._started = True

    def stop(self):
        """Terminate the bash shell."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return
        self._process.terminate()

    async def run(self, command: str):
        """Execute a command in the bash shell."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return ToolResult(
                system="tool must be restarted",
                error=f"bash has exited with returncode {self._process.returncode}",
            )
        if self._timed_out:
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            )

        # we know these are not None because we created the process with PIPEs
        assert self._process.stdin
        assert self._process.stdout
        assert self._process.stderr

        # send command to the process
        self._process.stdin.write(command.encode() + f"; echo '{self._sentinel}'\n".encode())
        await self._process.stdin.drain()

        # read output from the process, until the sentinel is found
        try:
            async with asyncio.timeout(self._timeout):
                while True:
                    await asyncio.sleep(self._output_delay)
                    # if we read directly from stdout/stderr, it will wait forever for
                    # EOF. use the StreamReader buffer directly instead.
                    output = (
                        self._process.stdout._buffer.decode()
                    )  # pyright: ignore[reportAttributeAccessIssue]
                    if self._sentinel in output:
                        # strip the sentinel and break
                        output = output[: output.index(self._sentinel)]
                        break
        except asyncio.TimeoutError:
            self._timed_out = True
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            ) from None

        if output.endswith("\n"):
            output = output[:-1]

        error = self._process.stderr._buffer.decode()  # pyright: ignore[reportAttributeAccessIssue]
        if error.endswith("\n"):
            error = error[:-1]

        # clear the buffers so that the next output can be read correctly
        self._process.stdout._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]
        self._process.stderr._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]

        return CLIResult(output=output, error=error)


class BashTool(BaseBashTool, BaseAnthropicTool):
    """
    A tool that allows the agent to run bash commands.
    The tool parameters are defined by Anthropic and are not editable.
    """

    name: ClassVar[Literal["bash"]] = "bash"
    api_type: ClassVar[Literal["bash_20250124"]] = "bash_20250124"
    _timeout: float = 120.0  # seconds

    def __init__(self, computer: Computer):
        """Initialize the bash tool.

        Args:
            computer: Computer instance for executing commands
        """
        # Initialize the base bash tool first
        BaseBashTool.__init__(self, computer)
        # Then initialize the Anthropic tool
        BaseAnthropicTool.__init__(self)
        # Initialize bash session
        self._session = _BashSession()

    async def __call__(self, command: str | None = None, restart: bool = False, **kwargs):
        """Execute a bash command.

        Args:
            command: The command to execute
            restart: Whether to restart the shell (not used with computer interface)

        Returns:
            Tool execution result

        Raises:
            ToolError: If command execution fails
        """
        if restart:
            return ToolResult(system="Restart not needed with computer interface.")

        if command is None:
            raise ToolError("no command provided.")

        try:
            async with asyncio.timeout(self._timeout):
                stdout, stderr = await self.computer.interface.run_command(command)
                return CLIResult(output=stdout or "", error=stderr or "")
        except asyncio.TimeoutError as e:
            raise ToolError(f"Command timed out after {self._timeout} seconds") from e
        except Exception as e:
            raise ToolError(f"Failed to execute command: {str(e)}")

    def to_params(self) -> Dict[str, Any]:
        """Convert tool to API parameters.

        Returns:
            Dictionary with tool parameters
        """
        return {"name": self.name, "type": self.api_type}
