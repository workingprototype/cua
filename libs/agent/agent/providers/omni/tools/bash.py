"""Provider-agnostic implementation of the BashTool."""

import logging
from typing import Any, Dict

from computer.computer import Computer

from ....core.tools.bash import BaseBashTool
from ....core.tools import ToolResult


class OmniBashTool(BaseBashTool):
    """A provider-agnostic implementation of the bash tool."""

    name = "bash"
    logger = logging.getLogger(__name__)

    def __init__(self, computer: Computer):
        """Initialize the BashTool.

        Args:
            computer: Computer instance, may be used for related operations
        """
        super().__init__(computer)

    def to_params(self) -> Dict[str, Any]:
        """Convert tool to provider-agnostic parameters.

        Returns:
            Dictionary with tool parameters
        """
        return {
            "name": self.name,
            "description": "A tool that allows the agent to run bash commands",
            "parameters": {
                "command": {"type": "string", "description": "The bash command to execute"},
                "restart": {
                    "type": "boolean",
                    "description": "Whether to restart the bash session",
                },
            },
        }

    async def __call__(self, **kwargs) -> ToolResult:
        """Execute the bash tool with the provided arguments.

        Args:
            command: The bash command to execute
            restart: Whether to restart the bash session

        Returns:
            ToolResult with the command output
        """
        command = kwargs.get("command")
        restart = kwargs.get("restart", False)

        if not command:
            return ToolResult(error="Command is required")

        self.logger.info(f"Executing bash command: {command}")
        exit_code, stdout, stderr = await self.run_command(command)

        output = stdout
        error = None

        if exit_code != 0:
            error = f"Command exited with code {exit_code}: {stderr}"

        return ToolResult(output=output, error=error)
