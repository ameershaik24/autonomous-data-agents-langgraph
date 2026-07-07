import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
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
