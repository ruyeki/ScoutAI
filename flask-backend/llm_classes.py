from langgraph.graph.message import add_messages, AnyMessage
from typing import TypedDict, Annotated
from rapidfuzz import fuzz


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list[AnyMessage], add_messages]

class Assistant:
    def __init__(self, chain):
        self.chain = chain

    def __call__(self, state: dict) -> dict:
        # Expect the state to include the user's message under a key, e.g., "message"
        user_message = state.get("message")
        if not user_message:
            raise ValueError("No 'message' key found in state.")

        # Invoke your chain with the user's input
        result = self.chain.invoke({"input": user_message})
        # Store the result in the state. Here we're using 'assistant_output' as the key.
        state["assistant_output"] = result.context
        return state

def is_statistical_question(state: dict) -> bool:
    message = state.get("message", "")
    statistical_keywords = [
        "average", "mean", "percentage", "total", "points",
        "rebounds", "assists", "statistic", "game stats"
    ]
    # Similarity threshold: adjust as needed (0-100 scale)
    threshold = 80  

    # Compare each keyword with the user message using fuzzy matching
    for keyword in statistical_keywords:
        similarity = fuzz.partial_ratio(keyword.lower(), message.lower())
        if similarity > threshold:
            return True
    return False

def start_node(state):
    """Initialize the conversation state"""
    return state
