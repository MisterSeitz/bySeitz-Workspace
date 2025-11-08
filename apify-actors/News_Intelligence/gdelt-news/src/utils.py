from __future__ import annotations

from apify import Actor
from langchain_core.messages import ToolMessage
from typing import TypedDict, List, Dict, Any


# Define the type for the message structure expected by log_state
class LogStateMessage(TypedDict):
    """Simplified type definition for messages expected in the state."""
    name: str
    content: str
    tool_calls: List[Dict[str, Any]]


class UtilsWorkflowState(TypedDict):
    """The type of the state object used for logging, expected to contain messages."""
    messages: List[LogStateMessage]


def log_state(state: UtilsWorkflowState) -> None:
    """
    Log the state of the graph, particularly focusing on LLM messages 
    and tool calls/results.

    Uses the `Actor.log.debug` method to log the state of the graph.

    Args:
        state: The state of the graph, containing a list of messages.
    """
    if 'messages' not in state or not state['messages']:
        Actor.log.debug("State has no messages to log.")
        return

    message = state['messages'][-1]
    
    # Traverse all tool messages and print them 
    # if multiple tools are called in parallel (showing tool results)
    if isinstance(message, ToolMessage):
        # Go backwards until the original message that triggered the tool call
        for _message in state['messages'][::-1]:
            if hasattr(_message, 'tool_calls'):
                break
            Actor.log.debug('-------- Tool Result --------')
            # Use getattr for robustness if 'name' or 'content' is missing
            Actor.log.debug('Tool: %s', getattr(_message, 'name', 'N/A'))
            Actor.log.debug('Result: %s', getattr(_message, 'content', 'N/A'))

    Actor.log.debug('-------- Message --------')
    Actor.log.debug('Message: %s', message)

    # Print all tool calls in the current message
    if hasattr(message, 'tool_calls'):
        for tool_call in getattr(message, 'tool_calls', []):
            Actor.log.debug('-------- Tool Call --------')
            Actor.log.debug('Tool: %s', tool_call.get('name', 'N/A'))
            Actor.log.debug('Args: %s', tool_call.get('args', 'N/A'))