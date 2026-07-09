import os
import re
import sqlite3
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from pypdf import PdfReader
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

    reader = PdfReader(pdf_path)
    full_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text.append(text)

    # Combine all pages and clean whitespaces
    content = " ".join(full_text)
    clean_content = re.sub(r"\s*\n\s*", " ", content)
    clean_content = re.sub(r" +", " ", clean_content)

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


@tool
def execute_sql_query(query: str) -> str:
    """Executes a SQL query against the company_sales.db SQLite database and returns the results or the database error message."""
    db_path = "company_sales.db"

    try:
        conn = sqlite3.connect(db_path)
        # Configure rows to be returned as dictionaries for cleaner upstream parsing
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "Query executed successfully, but returned 0 results."

        # Convert rows to a list of standard dictionaries
        result = [dict(row) for row in rows]
        return str(result)

    except sqlite3.Error as e:
        # Returning the raw error string is vital for the agent's self-correction loop
        return f"Database Error: {str(e)}"


# Bind the tool to our model specifically for the SQL Engineer Node
sql_llm_with_tools = llm.bind_tools([execute_sql_query])


SQL_ENGINEER_PROMPT = """You are an Expert Data Engineer specializing in writing safe, highly precise SQL queries.
Your objective is to execute the database retrieval steps outlined in the overall plan.

Database Schema Context:
- Table: `customers`
  * customer_id (INTEGER, PRIMARY KEY)
  * company_name (TEXT)
  * tier (TEXT) -> values: 'Enterprise', 'Mid-Market', 'SMB'
  * region (TEXT)
- Table: `orders`
  * order_id (INTEGER, PRIMARY KEY)
  * customer_id (INTEGER, FOREIGN KEY referencing customers.customer_id)
  * order_date (DATE)
  * revenue (REAL)
  * product_category (TEXT)

Qualitative Context Extracted from Operations PDF (Use this to find specific names, regions, or dates mentioned by the user):
{pdf_context}

The Overall Plan:
{plan_steps}

Look at the plan steps and use the `execute_sql_query` tool to retrieve the exact data required.
Do not hallucinate table names or columns. Only pull data that directly answers the plan objectives.
"""


def sql_engineer_node(state: MultiAgentDataState) -> Dict[str, Any]:
    print("\n--- ENTERING: SQL ENGINEER NODE ---")

    # Safely pull qualitative context from state, or provide a default fallback
    pdf_context = state.get("pdf_context", "No PDF context extracted yet.")
    plan_str = "\n".join(
        [f"{i+1}. {step}" for i, step in enumerate(state["plan_steps"])]
    )

    # Inject our state variables into the system prompt
    system_instructions = SQL_ENGINEER_PROMPT.format(
        pdf_context=pdf_context, plan_steps=plan_str
    )

    # Prepend system instructions to the full message history
    messages = [HumanMessage(content=system_instructions)] + state["messages"]

    # Invoke the LLM
    response = sql_llm_with_tools.invoke(messages)

    # Check if the model generated a tool call (i.e., wrote a SQL query)
    current_query = ""
    if response.tool_calls:
        # Extract the query string from the first tool call arguments
        current_query = response.tool_calls[0]["args"].get("query", "")
        print(f"SQL Engineer Generated Query:\n>>> {current_query}")

    return {"messages": [response], "sql_query": current_query}
