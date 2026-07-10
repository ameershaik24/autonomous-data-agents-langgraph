## 10th July 2026

1. Last week, after getting the first draft of the complete multi agents code using langgraph, by leveraging gemini for all code, trying to run it gave these warnings in console

   ```
   LangGraph Multi-Agent Mesh Compiled Successfully!

   Adding a node to a graph that has already been compiled. This will not be reflected in the compiled graph.

   Adding an edge to a graph that has already been compiled. This will not be reflected in the compiled graph.

   Starting Multi-Agent Orchestration Testing...
   ```
    **Issue**: This was happening because the graph (containing agents via nodes, edges) was complied before adding the "final_reporter" node and linking it using an edge.

    **Fix**: So, moved this line `app = workflow.compile()` after adding all the nodes, edges and conditional edges to the state graph

   ---

2. Last week, the initial code given by Gemini to read a PDF file using simple `f.read()` was giving this below error
   ```
   UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3 in position 10: invalid continuation byte
   ```
   **Issue**: PDFs are complex binary files and not plain text files to be able to read them as UTF-8 text files.

   **Fix**: Used `pypdf` python package to read the PDF document.
