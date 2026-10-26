#=====================================================================
# graph.py - wires all 6 patterns into one graph
#=====================================================================
# state.py   -> the shared notebook
# patterns/  -> the nodes, one file per pattern
# graph.py   -> the edges, which decide the ORDER
#
# order we follow here: add nodes -> add edges -> compile
#=====================================================================

from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

from state import SupportState
from patterns.p1_sequential import clean_node, summary_node
from patterns.p2_parallel import sentiment_node, urgency_node, abuse_node
from patterns.p3_routing import classifier_node, route_query
from patterns.p4_rag import billing_rag_node, tech_rag_node, general_node
from patterns.p5_loop_tools import (
    writer_node, tool_node, extract_draft_node, reviewer_node,
    should_use_tool, should_stop_looping,
)
from patterns.p6_human_in_loop import human_review_node, should_finish

graph = StateGraph(SupportState)

#---------------------------------------------------------------------
# nodes
#---------------------------------------------------------------------

#pattern 1
graph.add_node("clean", clean_node)
graph.add_node("summary", summary_node)

#pattern 2
graph.add_node("sentiment", sentiment_node)
graph.add_node("urgency", urgency_node)
graph.add_node("abuse", abuse_node)

#pattern 3
graph.add_node("classifier", classifier_node)

#pattern 4
graph.add_node("billing_rag", billing_rag_node)
graph.add_node("tech_rag", tech_rag_node)
graph.add_node("general", general_node)

#pattern 5
graph.add_node("writer", writer_node)
graph.add_node("tools", tool_node)
graph.add_node("extract_draft", extract_draft_node)
graph.add_node("reviewer", reviewer_node)

#pattern 6
graph.add_node("human_review", human_review_node)

#---------------------------------------------------------------------
# edges
#---------------------------------------------------------------------

#pattern 1 - sequential
graph.add_edge(START, "clean")
graph.add_edge("clean", "summary")

#pattern 2 - parallel (one node fans out to three, then all three must finish before classifier)
graph.add_edge("summary", "sentiment")
graph.add_edge("summary", "urgency")
graph.add_edge("summary", "abuse")
graph.add_edge(["sentiment", "urgency", "abuse"], "classifier")

#pattern 3 - routing (route_query returns the name of the next node)
graph.add_conditional_edges("classifier", route_query)

#pattern 4 - every route ends at the writer
graph.add_edge("billing_rag", "writer")
graph.add_edge("tech_rag", "writer")
graph.add_edge("general", "writer")

#pattern 5 - loop with tools
graph.add_conditional_edges("writer", should_use_tool)        # tools or extract_draft
graph.add_edge("tools", "writer")                             # tool result goes back to the writer
graph.add_edge("extract_draft", "reviewer")
graph.add_conditional_edges("reviewer", should_stop_looping)  # writer or human_review

#pattern 6 - human in the loop (route to END or back to the writer)
graph.add_conditional_edges("human_review", should_finish)

#---------------------------------------------------------------------
# compile
#---------------------------------------------------------------------

#the checkpointer saves the state at the pause, without it interrupt() cannot resume
checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)
