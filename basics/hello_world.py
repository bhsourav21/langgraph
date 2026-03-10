from typing import TypedDict
import os
import sys

from langgraph.pregel.main import Output

# Ensure sibling 'util' package is importable without changing directories
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from langgraph.graph import END, START, StateGraph
from util.langgraph_util import display

class HelloWorldState(TypedDict):
    message: str
    id: int

def hello(state: HelloWorldState):
    print(f"Hello Node: {state['message']}")
    return {"message": "Hello "+ state['message']}

def bye(state: HelloWorldState):
    print(f"Bye Node: {state['message']}")
    return {"message": "Bye "+ state['message']}

graph = StateGraph(HelloWorldState)
graph.add_node("hello", hello)
graph.add_node("bye", bye)

graph.add_edge(START, "hello")
graph.add_edge("hello", "bye")
graph.add_edge("bye", END)
            # OR #
# graph.add_edge("hello", "bye")
# graph.add_edge("bye", END)
# graph.set_entry_point("hello")

runnable = graph.compile()
display(runnable)
output = runnable.invoke({"message": "Sourav"})
print(output)