from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from langgraph.types import StreamWriter
from sqlalchemy import values


class HelloWorldState(TypedDict):
    message: str


def hello(state: HelloWorldState, writer: StreamWriter):
    # TODO: Write Custom Keys
    writer({"custom_key":"custom_value"})
    return {"message": "Hello " + state['message']}


def bye(state: HelloWorldState):
    return {"message": "Bye " + state['message']}


# Define the async graph
graph = StateGraph(HelloWorldState)
graph.add_node("hello", hello)
graph.add_node("bye", bye)

graph.add_edge(START, "hello")
graph.add_edge("hello", "bye")
graph.add_edge("bye", END)

runnable = graph.compile()

# TODO: Stream
# for chunk in runnable.stream({"message": "Sourav"}, stream_mode="values"):
# for chunk in runnable.stream({"message": "Sourav"}, stream_mode="updates"):
# for chunk in runnable.stream({"message": "Sourav"}, stream_mode="custom"):
for chunk in runnable.stream({"message": "Sourav"}, stream_mode="debug"):
    print(chunk)
