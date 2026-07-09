import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from state import MultiAgentDataState

load_dotenv()

# Initialize our primary LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

PLANNER_PROMPT = """You are the Lead Project Planner for an advanced enterprise data analytics team.
Your job is to break down a complex user business request into a clear, sequential set of execution steps.

You have access to two distinct data systems:
1. An unstructured PDF Document containing qualitative context, incident logs, regional issues, and timelines.
2. A relational SQL Database containing raw transactional numbers, customer records, and order metrics.

Analyze the user's request and return a structured plan as a numbered list of tasks.
Be highly specific about which step requires extracting data from the PDF and which step requires querying the SQL database.

User Request: {user_query}

Provide the response strictly as a clean numbered list of actions, one per line. Do not include introductory text or conclusions.
"""


def planner_node(state: MultiAgentDataState) -> Dict[str, Any]:
    print("\n--- ENTERING: PLANNER NODE ---")

    # Extract the very first user message from the message history
    user_query = state["messages"][0].content

    # Format prompt and invoke the LLM
    prompt = ChatPromptTemplate.from_template(PLANNER_PROMPT)
    chain = prompt | llm
    response = chain.invoke({"user_query": user_query})

    # Parse the numbered lines into a list of strings
    raw_steps = response.content.strip().split("\n")
    cleaned_steps = [step.strip() for step in raw_steps if step.strip()]

    print(f"Generated Plan Steps:\n" + "\n".join([f"- {s}" for s in cleaned_steps]))

    # Update the custom graph state variables
    return {
        "plan_steps": cleaned_steps,
        "messages": [
            response
        ],  # This appends the Planner's thought process to the conversation history
    }


@tool
def search_operations_pdf(query: str) -> str:
    """Searches the Q1 2026 Operations & Support Incident Review PDF for qualitative operational context,
    regional issues, dates, and account management notes."""
    # Production note: In a real pipeline, this would run a hybrid lexical/dense retrieval vector search on Pinecone/Milvus/Qdrant.
    # For my local setup, i'll implement a clean fallback that reads the mock file directly.
    pdf_path = "Q1_2026_Operations_Review.pdf"

    if not os.path.exists(pdf_path):
        return "Error: Q1_2026_Operations_Review.pdf file not found."

    with open(pdf_path, "r") as f:
        content = f.read()

    # Simulate high-context keyword extraction to mimic a semantic search response
    return (
        f"--- Retrieved Semantically Correlated Context from {pdf_path} ---\n{content}"
    )


# Bind the tool to our model specifically for the PDF Extractor Agent
pdf_llm_with_tools = llm.bind_tools([search_operations_pdf])


PDF_EXTRACTOR_PROMPT = """You are an Expert Research Agent specializing in parsing unstructured corporate data.
Your objective is to execute the parts of the following plan that require qualitative context from our operational reviews.

The Overall Plan:
{plan_steps}

Look at the plan steps and use the `search_operations_pdf` tool to retrieve the relevant information.
Synthesize the facts found in the document and save them clearly into the pipeline context.
"""


def pdf_extractor_node(state: MultiAgentDataState) -> Dict[str, Any]:
    print("\n--- ENTERING: PDF EXTRACTOR NODE ---")

    # Format the prompt context
    plan_str = "\n".join(
        [f"{i+1}. {step}" for i, step in enumerate(state["plan_steps"])]
    )
    system_instructions = PDF_EXTRACTOR_PROMPT.format(plan_steps=plan_str)

    # Construct a localized message chain for this node
    messages = [HumanMessage(content=system_instructions)] + state["messages"]

    # Invoke the LLM bound with tools
    response = pdf_llm_with_tools.invoke(messages)

    # If the LLM decides it needs to run the tool, we will return the updated variables
    # LangGraph pre-built ToolNode or a custom edge will handle executing the actual tool next.
    return {"messages": [response]}
