import os
import re
import sqlite3
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from pypdf import PdfReader
from state import MultiAgentDataState

load_dotenv()

script_dir = os.path.dirname(os.path.abspath(__file__))

# Initialize our primary LLM
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)

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
    pdf_filename = "Q1_2026_Operations_Review.pdf"
    pdf_path = os.path.join(script_dir, pdf_filename)

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
    return f"--- Retrieved Semantically Correlated Context from {pdf_filename} ---\n{content}"


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
    db_name = "company_sales.db"
    db_path = os.path.join(script_dir, db_name)

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


# 1. Combine all tools into a single node that handles execution
tools = [search_operations_pdf, execute_sql_query]
tool_node = ToolNode(tools)


# 2. Add an optional State Sync Node (Crucial for multi-agent handoffs)
# While ToolNode appends raw ToolMessages, we want to extract the results
# into our custom state variables (pdf_context, sql_result) so downstream agents can read them easily.
def state_synchronizer_node(state: MultiAgentDataState) -> Dict[str, Any]:
    print("\n--- ENTERING: STATE SYNCHRONIZER NODE ---")

    updates = {}
    last_message = state["messages"][-1]

    # If the last message came from a tool execution, let's extract it into our structured state
    if isinstance(last_message, ToolMessage):
        if last_message.name == "search_operations_pdf":
            print("Syncing extracted PDF data into 'pdf_context'...")
            updates["pdf_context"] = last_message.content

        elif last_message.name == "execute_sql_query":
            raw_content = last_message.content

            if "Database Error" in raw_content:
                print(f"Syncing DB Error: {raw_content}")
                updates["sql_error"] = raw_content
                updates["sql_result"] = []
            else:
                print("Syncing SQL results into 'sql_result'...")
                # Clear out old errors and save the list
                updates["sql_error"] = ""
                updates["sql_result"] = raw_content

    return updates


def final_reporter_node(state: MultiAgentDataState) -> Dict[str, Any]:
    print("\n--- ENTERING: FINAL REPORTER NODE ---")
    print(
        f"Final Gathered Context to synthesize:\n- PDF Data: {state.get('pdf_context')}\n- SQL Data: {state.get('sql_result')}"
    )
    return {
        "messages": [AIMessage(content="Pipeline execution finished successfully!")]
    }


def route_pdf_extractor(state: MultiAgentDataState) -> str:
    """Decides if the PDF extractor needs to run tools or hand off to the SQL Engineer."""
    last_message = state["messages"][-1]

    # If the LLM called a tool, route to the tool node
    if last_message.tool_calls:
        return "tools"

    # If no tool call was made, it means the agent is done gathering PDF info. Proceed to SQL.
    return "sql_engineer"


def route_sql_engineer(state: MultiAgentDataState) -> str:
    """Controls the self-correction cycle for the SQL Engineer."""
    last_message = state["messages"][-1]

    # If the LLM called a tool to query the DB, send it to the tools node
    if last_message.tool_calls:
        return "tools"

    # If the tool already executed but threw an error, check the state
    if state.get("sql_error"):
        print(
            ">>> Self-Correction Triggered: Routing back to SQL Engineer to fix syntax error."
        )
        return "sql_engineer"

    # If there are no tool calls and no errors, the data was fetched successfully! Proceed to final synthesis.
    return "final_reporter"


# Synchronizer decides where to return control based on what tool just ran
def route_after_sync(state: MultiAgentDataState) -> str:
    last_message = state["messages"][
        -2
    ]  # Look behind the tool message to see who called it
    if "search_operations_pdf" in str(last_message):
        return "pdf_extractor"
    return "sql_engineer"


# Initialize the graph with our custom state schema
workflow = StateGraph(MultiAgentDataState)

# 1. Add ALL nodes first
workflow.add_node("planner", planner_node)
workflow.add_node("pdf_extractor", pdf_extractor_node)
workflow.add_node("sql_engineer", sql_engineer_node)
workflow.add_node("tools", tool_node)
workflow.add_node("synchronizer", state_synchronizer_node)
workflow.add_node("final_reporter", final_reporter_node)


# 2. Add ALL structural deterministic edges
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "pdf_extractor")
# When tools finish running for the PDF, sync data and go right back to the PDF agent to review it
workflow.add_edge("tools", "synchronizer")
workflow.add_edge("final_reporter", END)


# 3. Add the conditional edges that manage tool execution loops
workflow.add_conditional_edges(
    "pdf_extractor",
    route_pdf_extractor,
    {"tools": "tools", "sql_engineer": "sql_engineer"},
)

workflow.add_conditional_edges(
    "synchronizer",
    route_after_sync,
    {"pdf_extractor": "pdf_extractor", "sql_engineer": "sql_engineer"},
)

workflow.add_conditional_edges(
    "sql_engineer",
    route_sql_engineer,
    {
        "tools": "tools",
        "sql_engineer": "sql_engineer",  # Self-correction loop path
        "final_reporter": "final_reporter",
    },
)


# 4. Now, compile the graph
app = workflow.compile()
print("LangGraph Multi-Agent Mesh Compiled Successfully!")


if __name__ == "__main__":
    test_query = (
        "Check our Q1 operations review PDF to see what major issue happened in the North region. "
        "Then, pull the total revenue numbers from the SQL database for any Enterprise customer in that region "
        "to check their account health."
    )

    print("Starting Multi-Agent Orchestration Testing...")
    initial_state = {"messages": [HumanMessage(content=test_query)]}
    app.invoke(initial_state)
