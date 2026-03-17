import os
import asyncio
from typing import List, TypedDict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Medical Knowledge Sources (Example URLs)
medical_info_urls = [
    "https://www.who.int/health-topics",
    "https://www.mayoclinic.org/diseases-conditions",
    "https://medlineplus.gov/symptoms.html",
    "https://www.webmd.com/a-to-z-guides/diseases-conditions",
]

# Load Medical Data
docs = [WebBaseLoader(url).load() for url in medical_info_urls]
docs_list = [item for sublist in docs for item in sublist]

# Split Medical Information
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=500, chunk_overlap=50
)
doc_splits = text_splitter.split_documents(docs_list)

# Store and Retrieve Medical Data with ChromaDB
vectorstore = Chroma.from_documents(
    documents=doc_splits,
    collection_name="medical-diagnosis",
    embedding=OpenAIEmbeddings(),
)
retriever = vectorstore.as_retriever()

# Prompt for Medical Diagnosis
prompt = ChatPromptTemplate.from_template(
    """
    You are an AI doctor providing preliminary medical diagnoses based on symptoms.
    Use the retrieved medical information to analyze the possible causes.

    Patient Symptoms: {question}
    Relevant Medical Information: {context}
    AI-Powered Diagnosis:
    """
)
model = ChatOpenAI()
diagnosis_chain = prompt | model | StrOutputParser()

# Define Graph State
class MedicalDiagnosisGraphState(TypedDict):
    question: str
    retrieved_data: List[str]
    diagnosis: str

# TODO: Implement the retrieve_medical_data function
def retrieve_medical_data(state):
    print("---RETRIEVE MEDICAL DATA---")
    question = state["question"]
    retrieved_medical_data = retriever.invoke(question)
    return {"question": question, "retrieved_medical_data": retrieved_medical_data}

# TODO: Implement the analyze_medical_diagnosis function
def analyze_medical_diagnosis(state):
    print("---GENERATE MEDICAL DIAGNOSTIC SUMMARY---")
    question = state["question"]
    retrieved_medical_data = retriever.invoke(question)
    diagnosis = diagnosis_chain.invoke({"question": question, "context": retrieved_medical_data})
    return {"question": question, "retrieved_medical_data": retrieved_medical_data, "diagnosis": diagnosis}

# TODO: Implement the create_medical_diagnosis_workflow function
def create_medical_diagnosis_workflow():
    workflow = StateGraph(MedicalDiagnosisGraphState)
    workflow.add_node("retrieve_medical_data", retrieve_medical_data)
    workflow.add_node("analyze_medical_diagnosis", analyze_medical_diagnosis)
    workflow.add_edge(START, "retrieve_medical_data")
    workflow.add_edge("retrieve_medical_data", "analyze_medical_diagnosis")
    workflow.add_edge("analyze_medical_diagnosis", END)
    return workflow.compile()

# Execute the Workflow
medical_diagnosis_graph = create_medical_diagnosis_workflow()

inputs = {"question": "I have a persistent cough, fever, and shortness of breath. What could it be?"}

response = medical_diagnosis_graph.invoke(
    inputs,
)

print("\n--- AI MEDICAL DIAGNOSIS ---")
print(response["diagnosis"])
