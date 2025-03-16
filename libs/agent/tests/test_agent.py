# """Basic tests for the agent package."""

# import pytest
# from agent import OmniComputerAgent, LLMProvider
# from agent.base.agent import BaseComputerAgent
# from computer import Computer

# def test_agent_import():
#     """Test that we can import the OmniComputerAgent class."""
#     assert OmniComputerAgent is not None
#     assert LLMProvider is not None

# def test_agent_init():
#     """Test that we can create an OmniComputerAgent instance."""
#     agent = OmniComputerAgent(
#         provider=LLMProvider.OPENAI,
#         use_host_computer_server=True
#     )
#     assert agent is not None

# @pytest.mark.skipif(not hasattr(ComputerAgent, '_ANTHROPIC_AVAILABLE'), reason="Anthropic provider not installed")
# def test_computer_agent_anthropic():
#     """Test creating an Anthropic agent."""
#     agent = ComputerAgent(provider=Provider.ANTHROPIC)
#     assert isinstance(agent._agent, BaseComputerAgent)

# def test_computer_agent_invalid_provider():
#     """Test creating an agent with an invalid provider."""
#     with pytest.raises(ValueError, match="Unsupported provider"):
#         ComputerAgent(provider="invalid_provider")

# def test_computer_agent_uninstalled_provider():
#     """Test creating an agent with an uninstalled provider."""
#     with pytest.raises(NotImplementedError, match="OpenAI provider not yet implemented"):
#         # OpenAI provider is not implemented yet
#         ComputerAgent(provider=Provider.OPENAI)

# @pytest.mark.asyncio
# @pytest.mark.skipif(not hasattr(ComputerAgent, '_ANTHROPIC_AVAILABLE'), reason="Anthropic provider not installed")
# async def test_agent_cleanup():
#     """Test agent cleanup."""
#     agent = ComputerAgent(provider=Provider.ANTHROPIC)
#     await agent.cleanup()  # Should not raise any errors

# @pytest.mark.asyncio
# @pytest.mark.skipif(not hasattr(ComputerAgent, '_ANTHROPIC_AVAILABLE'), reason="Anthropic provider not installed")
# async def test_agent_direct_initialization():
#     """Test direct initialization of the agent."""
#     # Create with default computer
#     agent = ComputerAgent(provider=Provider.ANTHROPIC)
#     try:
#         # Should not raise any errors
#         await agent.run("test task")
#     finally:
#         await agent.cleanup()

#     # Create with custom computer
#     custom_computer = Computer(
#         display="1920x1080",
#         memory="8GB",
#         cpu="4",
#         os="macos",
#         use_host_computer_server=False,
#     )
#     agent = ComputerAgent(provider=Provider.ANTHROPIC, computer=custom_computer)
#     try:
#         # Should not raise any errors
#         await agent.run("test task")
#     finally:
#         await agent.cleanup()

# @pytest.mark.asyncio
# @pytest.mark.skipif(not hasattr(ComputerAgent, '_ANTHROPIC_AVAILABLE'), reason="Anthropic provider not installed")
# async def test_agent_context_manager():
#     """Test context manager initialization of the agent."""
#     # Test with default computer
#     async with ComputerAgent(provider=Provider.ANTHROPIC) as agent:
#         # Should not raise any errors
#         await agent.run("test task")

#     # Test with custom computer
#     custom_computer = Computer(
#         display="1920x1080",
#         memory="8GB",
#         cpu="4",
#         os="macos",
#         use_host_computer_server=False,
#     )
#     async with ComputerAgent(provider=Provider.ANTHROPIC, computer=custom_computer) as agent:
#         # Should not raise any errors
#         await agent.run("test task")
