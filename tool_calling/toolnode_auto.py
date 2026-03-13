import os
import sys

from langgraph.graph import END, START, StateGraph, MessagesState
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

# Ensure sibling 'util' package is importable when running as a script
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from util.langgraph_util import display

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@tool
def get_restaurant_recommendations(location: str):
    """Provides a single top restaurant recommendation for a given location."""
    recommendations = {
        "munich": ["Hofbräuhaus", "Augustiner-Keller", "Tantris"],
        "new york": ["Le Bernardin", "Eleven Madison Park", "Joe's Pizza"],
        "paris": ["Le Meurice", "L'Ambroisie", "Bistrot Paul Bert"],
    }
    return recommendations.get(location.lower(), ["No recommendations available."])


@tool
def book_table(restaurant: str, time: str):
    """Books a table at a specified restaurant and time."""
    return f"Table booked at {restaurant} for {time}."


# Bind the tool to the model
tools = [get_restaurant_recommendations, book_table]
model = ChatOpenAI().bind_tools(tools)
tool_node = ToolNode(tools)


# TODO: Define functions for the workflow
def call_model(state: MessagesState):
    messages = state["messages"]
    response = model.invoke(messages)
    # `MessagesState` expects a list of messages; append the model response.
    return {"messages": [response]}


# TODO: Define Conditional Routing
def should_continue(state: MessagesState):
    messages = state["messages"]
    last_message = messages[-1]

    if last_message.tool_calls:
        return "tools"
    return END


# TODO: Define the workflow

workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    path_map={"tools": "tools", END: END},
)
workflow.add_edge("tools", "agent")


graph= workflow.compile()

display(graph)
# First invoke - Get one restaurant recommendation
response = graph.invoke(
    {"messages": [HumanMessage(content="Can you recommend just one top restaurant in Munich? "
                                       "The response should contain just the restaurant name")]})

# TODO: Extract the recommended restaurant
recommended_restaurant = response["messages"][-1].content
print(f"recommended_restaurant:{recommended_restaurant}")
