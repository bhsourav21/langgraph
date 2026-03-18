import os
from typing import TypedDict
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Define the input state (Loan Application)
class LoanApplication(TypedDict):
    applicant_name: str
    credit_score: int
    loan_amount: float
    status: str
    decision: str


# Function to categorize loan application
def categorize_application(state: LoanApplication):
    print(f"Processing application: {state}")
    if state["credit_score"] >= 700:
        return Command(goto="approve")
    return Command(goto="review")


# Function to approve loans automatically
def approve_loan(state: LoanApplication):
    print(f"Loan approved for {state['applicant_name']} - Amount: {state['loan_amount']}")
    return Command(goto=END,update={"decision": f"Approved  {state['loan_amount']}"})


# TODO: Function to send loan applications for manual review using HITL
def manual_review(state: LoanApplication):
    print(f"Loan amount: {state['loan_amount']}")
    print(f"Credit score: {state['credit_score']}")
    value = interrupt({
        "question": "Are you okay approve the loan? Type yes or no."
    })
    if value == "yes":
        return Command(goto="approve")
    else:
        return Command(goto="reject")


# Function to reject loans
def reject_loan(state: LoanApplication):
    print(f"Loan rejected for {state['applicant_name']} - Amount: {state['loan_amount']}")
    return Command(goto=END,update={"decision": f"Rejected  {state['loan_amount']}"})


# Create the state graph
graph = StateGraph(LoanApplication)

# Add nodes
graph.add_node("categorization", categorize_application)
graph.add_node("approve", approve_loan)
graph.add_node("review", manual_review)
graph.add_node("reject", reject_loan)
graph.set_entry_point("categorization")

# Compile the workflow
loan_workflow = graph.compile(checkpointer=MemorySaver())

# Simulate loan applications with HITL
inputs = {"applicant_name": "Bob", "credit_score": 400, "loan_amount": 30000}
# inputs = {"applicant_name": "Bob", "credit_score": 701, "loan_amount": 30000}
thread = {"configurable": {"thread_id": 1}}


# Initial invocation
result = loan_workflow.invoke(inputs, config=thread)

# TODO: Handle the Interrupt and Provide Human Feedback
tasks = loan_workflow.get_state(config=thread).tasks
if len(tasks) > 0:
    task = tasks[0]
    question = task.interrupts[0].value.get("question")
    user_input = input(question)

    result = loan_workflow.invoke(Command(resume=user_input),config=thread)
    # Display results
    print("\n--- Final Decision ---")
    print(f"{result['decision']} (Amount: {inputs['loan_amount']})")