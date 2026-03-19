from typing import TypedDict, List
from langchain_openai import ChatOpenAI,OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
import psycopg
import requests
from langgraph.types import interrupt
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ---------------------- Define State ----------------------
class ClaimState(TypedDict):
    patient_id: str
    treatment_code: str
    claim_details: str
    patient_data: dict
    insurance_data: dict
    policy_docs: List[str]
    ai_validation_feedback: str
    final_decision: str
    _next: str  # ✅ Added _next for decision-making


# ---------------------- Constants ----------------------
FHIR_BASE_URL = "https://hapi.fhir.org/baseR4"

DB_CONFIG = {
    "dbname": "claims_db",
    "user": "postgres",
    "password": "Welcome234@",
    "host": "localhost"
}

llm = ChatOpenAI()

# Load policy documents for RAG
loader = TextLoader("insurance_data.txt")
documents = loader.load()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
chunks = text_splitter.split_documents(documents)

embeddings = OpenAIEmbeddings()
vector_store = Chroma.from_documents(chunks, embeddings)


# ---------------------- Step 1: Fetch Patient Data ----------------------
def fetch_patient_data(state: ClaimState):
    patient_id = state["patient_id"]
    response = requests.get(f"{FHIR_BASE_URL}/Patient/{patient_id}")
    if response.status_code == 200:
        state["patient_data"] = response.json()
    else:
        state["patient_data"] = {"error": "Patient not found"}
    
    return state



# ---------------------- Step 2: Fetch Insurance Data ----------------------
def fetch_patient_insurance(state: ClaimState):
    patient_id = state["patient_id"]
    response = requests.get(f"{FHIR_BASE_URL}/Coverage?patient={patient_id}")
    if response.status_code == 200:
        state["insurance_data"] = response.json()
    else:
        state["insurance_data"] = {"error": "Insurance details not found"}
    
    return state



# ---------------------- Step 3: Retrieve Policy Documents ----------------------
def retrieve_policy_docs(state: ClaimState):
    treatment_code = state["treatment_code"]
    query = f"Retrieve insurance policy details for {treatment_code}"
    docs = vector_store.search(query, k=4) #k=4 means return only top 4 documents within the search
    state["policy_docs"] = [doc.page_content for doc in docs]   
    
    return state


# ---------------------- Step 4: AI-Based Claim Validation ----------------------
def validate_claim(state: ClaimState):
    claim_text = f"""
    Clain Deatils: {state["claim_details"]}
    Patient Data: {state["patient_data"]}
    Insurance Coverage: {state['insurance_data']}
    Retrieved Policies: {state['policy_docs']}
    """

    response = llm.invoke(
        f"Validate the following claim. Should it be Approved, Rejected or need more info? {claim_text}"
    )

    state["ai_validation_feedback"] = response.content

    return state

# ---------------------- Step 5: Decision Node ----------------------
def claim_decision(state: ClaimState):
    decision_text = state["ai_validation_feedback"]

    if "more info" in decision_text.lower():
        state["final_decision"] = "Request More Info"
        state["_next"] = "human_review"
    elif "accept" in decision_text.lower():
        state["final_decision"] = "Approved"
        state["_next"] = "store_claim"
    elif "reject" in decision_text.lower():
        state["final_decision"] = "Rejected"
        state["_next"] = "store_claim"
    
    return state

# ---------------------- Step 6: Store Decision in Database ----------------------
def store_claim(state: ClaimState):
    conn = psycopg.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("insert into claims (patient_id, status,decision_details) values (%s, %s, %s)",
    (state['patient_id'], state['final_decision'], state["ai_validation_feedback"]))
    
    conn.commit()
    cur.close()
    conn.close()
    return state


# ---------------------- Step 7: Human Review ----------------------
def human_review(state: ClaimState):
    interrupt(
        {
        "feedback": state["ai_validation_feedback"]
        }
    )
    return state

# ---------------------- Build LangGraph Workflow ----------------------


def create_workflow():
    graph = StateGraph(ClaimState)
    graph.add_node("fetch_patient_data", fetch_patient_data)
    graph.add_node("fetch_patient_insurance", fetch_patient_insurance)
    graph.add_node("retrieve_policy_docs", retrieve_policy_docs)
    graph.add_node("validate_claim", validate_claim)
    graph.add_node("claim_decision", claim_decision)
    graph.add_node("store_claim", store_claim)
    graph.add_node("human_review", human_review)

    # ✅ Define workflow transitions
    graph.set_entry_point("fetch_patient_data")
    graph.add_edge("fetch_patient_data", "fetch_patient_insurance")
    graph.add_edge("fetch_patient_insurance", "retrieve_policy_docs")
    graph.add_edge("retrieve_policy_docs", "validate_claim")
    graph.add_edge("validate_claim", "claim_decision")
    graph.add_edge("human_review", "store_claim")

    # ✅ Decision-making edges
    graph.add_conditional_edges(
        "claim_decision",
        lambda state: state["_next"],
        {
            "store_claim": "store_claim",
            "human_review": "human_review"
        }
    )

    # ✅ Create an InMemoryCheckpointer
    checkpointer = MemorySaver()
    graph = graph.compile(checkpointer=checkpointer)
    return graph