# Autonomous Data Agents Pipeline using LangGraph

A production-grade, multi-agent AI framework built to autonomously orchestrate complex business intelligence tasks across unstructured documents (PDFs) and relational databases (SQL).

This system shifts away from brittle, linear LLM chains into a highly reliable, cyclic graph architecture capable of handling ambiguous user intents, managing state across multiple modalities, and self-correcting database execution errors at runtime.


## 🛠️ Tech Stack & Optimization Decisions
* **Orchestration:** LangGraph (StateGraph API)
* **LLM Engine:** Gemini Flash Architecture (Selected for sub-second latency, cost efficiency across high-volume agentic loops, and native tool-calling capabilities)
* **Document Ingestion:** PyMuPDF / Fitz (Optimized for rapid, layout-aware text extraction from multi-page corporate PDFs)
* **Structured Storage:** SQLite / Relational Database Engine
* **Development Environment:** Python 3, Dotenv, Git Versioning


## 🚀 Key Architectural Highlights

### 1. Explicit State Management (`MultiAgentDataState`)
Unlike standard conversational frameworks that store history as an ambiguous string block, this architecture utilizes a strongly typed, centralized custom state. Every agent node acts as a stateless function that receives the current global state, transforms it, and applies deterministic reducers to pass context (e.g., extracted schemas, error messages, and vector content) smoothly across the network.

### 2. Autonomous Self-Correction Loop
Production database agents frequently fail due to schema hallucinations or syntax errors. This pipeline implements a cyclic feedback edge: when the **SQL Engineer** generates an invalid query, the database runtime catches the raw exception and passes it back to the agent node. The agent analyzes the syntax error natively and automatically self-corrects the query without crashing the master application.

### 3. Granular Multi-Agent Separation of Concerns
Instead of relying on a single monolithic prompt, the workflow is split into specialized, low-context workers:
* **The Planner**: Decomposes high-level natural language ambiguity into a strict execution checklist.
* **The PDF Research Agent**: Isolates qualitative background data utilizing target tool extraction hooks.
* **The SQL Engineer**: Inspects relational interfaces and safely maps transactional records.
* **The Final Executive Reporter**: Synthesizes multi-modal inputs into structurally sound, markdown-formatted business intelligence summaries.


## 📊 End-to-End Execution Trace

```text
LangGraph Multi-Agent Mesh Compiled Successfully!
Starting Multi-Agent Orchestration Testing...

--- ENTERING: PLANNER NODE ---
Generated Plan Steps:
- 1. Extract the Q1 operations review PDF to identify the specific major issue reported in the North region.
- 2. Query the SQL database to retrieve the list of all customers categorized as "Enterprise" located within the North region.
- 3. Query the SQL database to aggregate the total revenue for the identified Enterprise customers in the North region for the Q1 period.
- 4. Cross-reference the identified major issue from the PDF with the revenue data to assess the impact on account health.

--- ENTERING: PDF EXTRACTOR NODE ---

--- ENTERING: STATE SYNCHRONIZER NODE ---
Syncing extracted PDF data into 'pdf_context'...

--- ENTERING: PDF EXTRACTOR NODE ---

--- ENTERING: SQL ENGINEER NODE ---
SQL Engineer Generated Query:
>>> SELECT customer_id, company_name FROM customers WHERE tier = 'Enterprise' AND region = 'North';

--- ENTERING: STATE SYNCHRONIZER NODE ---
Syncing SQL results into 'sql_result'...

--- ENTERING: SQL ENGINEER NODE ---
SQL Engineer Generated Query:
>>> SELECT SUM(revenue) as total_q1_revenue FROM orders WHERE customer_id = 1 AND order_date BETWEEN '2026-01-01' AND '2026-03-31';

--- ENTERING: STATE SYNCHRONIZER NODE ---
Syncing SQL results into 'sql_result'...

--- ENTERING: SQL ENGINEER NODE ---

--- ENTERING: FINAL REPORTER NODE ---

==================== FINAL EXECUTIVE REPORT ====================

# Executive Health Assessment Report: Q1 2026

## 1. Executive Summary
Q1 2026 was characterized by a period of operational volatility that directly impacted our North region service delivery. A critical 45% spike in support tickets during January, driven by severe API latency, created a significant friction point for our client base. While technical remediation was successfully achieved by February, the incident caused measurable reputational damage with our high-priority accounts. Operations stabilized by March, with successful onboarding of Mid-Market accounts, indicating that the underlying infrastructure issues have been resolved.

## 2. Financial Impact Assessment
The total Q1 revenue for the period stands at **$95,000.00**.

The primary financial risk stems from the dissatisfaction of **TechCorp Solutions**, our high-priority account. Due to the service degradation experienced in January and February, TechCorp Solutions has explicitly threatened to delay upcoming contract expansions. Given their status as a high-priority partner, the potential deferral of these expansions poses a direct threat to our projected revenue growth for the remainder of the fiscal year.

## 3. Account Health Status
**Status: Critical Risk**

*   **Rationale:** While the technical environment is now stable, the relationship health with TechCorp Solutions remains in a "Critical Risk" state. The threat to delay contract expansions indicates a loss of trust that cannot be recovered through technical stability alone. Immediate executive intervention is required to prevent churn or long-term revenue stagnation.

## 4. Actionable Recommendations
To mitigate the risk to our Q1 revenue and restore the partnership with TechCorp Solutions, the following actions are recommended:

*   **Executive Outreach:** Initiate a formal "Service Recovery" meeting between our Account Executive and the TechCorp Solutions leadership team to acknowledge the Q1 service failures and present our long-term stability roadmap.
*   **Root Cause Transparency:** Provide TechCorp Solutions with a summary of the technical remediation steps taken in February to demonstrate that the API latency issues have been permanently addressed.
*   **Incentivized Retention:** Evaluate the feasibility of offering a service-level credit or a value-add professional services engagement to incentivize the immediate signing of the pending contract expansions.
*   **North Region Monitoring:** Maintain heightened monitoring for the North region for the next 30 days to ensure that the recent stabilization remains consistent as we scale Mid-Market onboarding.

================================================================
```


## 📐 System Architecture & Agent Flow

Below is the architectural blueprint of the multi-agent orchestration mesh. It illustrates the stateless node execution, the centralized `MultiAgentDataState` boundary, and the cyclic self-correction loop that manages the SQL execution.

<p align="center">
  <img src="images/graph_data_agents_diagram.svg" alt="LangGraph Multi-Agent Architecture Diagram" width="700">
</p>

### Key Flow Mechanics Highlighted in the Diagram:

1. **State-Driven Routing**: Every **Agent Node** (blue) executes independently and outputs to a **Conditional Router Function** (oval). Rather than hardcoding connections, the routers dynamically direct the flow based on the current state's messages.
2. **Centralized Tool Execution**: If either the `pdf_extractor` or the `sql_engineer` requires external action, their respective conditional routers redirect the path to the centralized `tools` node (purple).
3. **The Synchronizer (Function Node)**: After any tool execution completes, the flow passes through the `synchronizer` (orange) to extract raw output strings into structured state variables before the `route_after_sync` router returns control back to the calling agent.
4. **Self-Correction & Terminal Synthesis**: If a database error occurs, the state is updated, and control loops seamlessly back to the `sql_engineer` to construct a corrected query. Once the data retrieval tasks are fully met without further tool requests, the flow transitions directly to the `final_reporter` for summary generation.


## 💻 Local Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ameershaik24/autonomous-data-agents-langgraph.git
   cd autonomous-data-agents-langgraph
   ```

2. **Set up virtual environment & install dependencies:** Python version - 3.12.4
   ```bash
   python3 -m venv agents-venv
   source agents-venv/bin/activate  # On Windows use `agents-venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:** Create a `.env` file in the root directory and append your access credentials:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

4. **Initialize Database and Boot Application:**
   ```bash
   python database.py
   python app.py
   ```
