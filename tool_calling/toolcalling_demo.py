import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@tool
def get_restaurant_recommendations(location: str):
    """Provides a list of top restaurant recommendations for a given location."""
    recommendations = {
        "munich": ["Hofbräuhaus", "Augustiner-Keller", "Tantris"],
        "new york": ["Le Bernardin", "Eleven Madison Park", "Joe's Pizza"],
        "paris": ["Le Meurice", "L'Ambroisie", "Bistrot Paul Bert"],
    }
    return recommendations.get(location.lower(), ["No recommendations available for this location."])


# TODO: Bind the tool to the model
tools = [get_restaurant_recommendations]
llm = ChatOpenAI()
llm_with_tools = llm.bind_tools(tools)


messages = [
    HumanMessage("Recommend some restaurants in Munich.")
]

#TODO: Invoke the llm
llm_output = llm_with_tools.invoke(messages)
print(f"llm_output:{llm_output}")