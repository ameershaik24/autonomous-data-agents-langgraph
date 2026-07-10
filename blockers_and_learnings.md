## 10th July 2026

1. **Blocker** - How to get an API key for an LLM (specifically Gemini since I already signed up on Google AI Studio) for this project?
   - The API key in the Free Tier is very limiting that even just one run of the script is reaching the RPM limit
   - While I was taking a backup of data in my Pixel 9a to give to repair, I came across this Google One offer for 3 months for Google AI Pro plan which costs me the same 130 rs. per month that I am paying now for 100 GB storage plan.
   - The benefit said this - Gemini app with 4x higher usage limits - this looked like the perfect thing for my needs - same monthly subscription fees for a limited time (3 monthis is a very sufficient enough for this project) but with higher usage limits. So subscribed to this - with a task created to cancel the subscription just before the 3 month offer expires.
   - After subscribing, I realized that this higher limit applies only in the Gemini app and AI studio interface and not for API Keys for Gemini.
   - Asked Gemini again for all the benefits of this google ai pro 5tb package. It said I'll also get $10 Monthly Google Cloud Credits - an aha! moment
   - So, I first upgraded my billing tier from Free tier to paid Tier 1 (adding a CC with E-mandate) which created a new google cloud billing account and then, figured out how to claim these credits on https://me.developers.google.com/benefits and linked them on the newly created google cloud billing account
   - Then, even with this credits in place, I was still seeing this message - "A credit balance above $0 is required to resume service." - this was some Google's new Prepay billing system things - which is, I have to purchase some minimum credits first, before the billing kicks in - which would then utilizie the $10 credits first and then the purchased credits. So, bought the minimum 1000 rs credits and started using the API key in the project.
   - Also, while doing all this, I happened to look at the Documentation link present in Google AI Studio and landed at the Pricing page - which shows the pricing for all the different LLM models from Gemini
   - Asked Gemini to suggest me the right model to use for this Langgraph Agents project considering this $10 credits. It suggested "gemini-3.1-flash-lite" with this line - "To give you an idea of how far this goes: $1.00 will get you roughly 4 million input tokens. Your $10 monthly developer credit essentially means you can run hundreds of thousands of multi-turn agent execution loops every month without ever touching your actual cash balance."

   **Learnings**:
   - Choosing the right LLM model for multi agents orchestration - keeping in mind the cost of tokens, latency of the model, llm capabilities - structured outputs and function calling.
   - Tiers in Google AI Studio and their Rate Limits. Credits Prepay vs Postpay. Minimum credits purchase needed to use the API key even with free $10 credits.
   - Google cloud billing account setup, Getting the free $10 credits into this billing account.
   - Google One AI Pro plan benefits page - https://me.developers.google.com/benefits


2. Last week, after getting the first draft of the complete multi agents code using langgraph, by leveraging gemini for all code, trying to run it gave these warnings in console

   ```
   LangGraph Multi-Agent Mesh Compiled Successfully!

   Adding a node to a graph that has already been compiled. This will not be reflected in the compiled graph.

   Adding an edge to a graph that has already been compiled. This will not be reflected in the compiled graph.

   Starting Multi-Agent Orchestration Testing...
   ```
    **Issue**: This was happening because the graph (containing agents via nodes, edges) was complied before adding the "final_reporter" node and linking it using an edge.

    **Fix**: So, moved this line `app = workflow.compile()` after adding all the nodes, edges and conditional edges to the state graph

   ---

3. Last week, the initial code given by Gemini to read a PDF file using simple `f.read()` was giving this below error
   ```
   UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 10: invalid continuation byte
   ```
   **Issue**: PDFs are complex binary files and not plain text files to be able to read them as UTF-8 text files.

   **Fix**: Used `pypdf` python package to read the PDF document.
