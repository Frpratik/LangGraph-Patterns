#=====================================================================
# PATTERN 3 - CONDITIONAL ROUTING
#=====================================================================
# idea      : the graph chooses its next step while it is running
# node      : classifier_node  (decides and saves the category)
# router    : route_query      (turns the category into a node name)
# reads     : clean_ticket, query_type
# writes    : query_type
# graph.py  : classifier -> billing_rag | tech_rag | general
#
# two pieces on purpose: the node does the thinking,
# the router function only translates the answer into a destination
#=====================================================================

from state import SupportState
from config import llm


def classifier_node(state: SupportState) -> dict:
    """Looks at the ticket and decides which path to take."""

    prompt = (
        "Classify the following support ticket into exactly one category: "
        "'billing', 'technical', or 'general'.\n\n"
        "Use 'billing' for payments, charges, invoices, plans, pricing, renewals, "
        "cancellation, or refunds.\n"
        "Use 'technical' for login, crashes, bugs, sync, errors, api, or data export.\n"
        "Use 'general' for greetings, thanks, or anything else.\n\n"
        f"Ticket: {state['clean_ticket']}\n\n"
        "Return only one word: billing, technical, or general."
    )
    response = llm.invoke(prompt)
    category = response.content.strip().lower()

    #the llm may add a dot or a capital letter, so we check for the word
    #anything unexpected becomes general so the graph always has a route
    if "billing" in category:
        category = "billing"
    elif "technical" in category:
        category = "technical"
    else:
        category = "general"

    return {"query_type": category}


def route_query(state: SupportState):
    """Router function - returns the NAME of the next node."""
    if state["query_type"] == "billing":
        return "billing_rag"
    elif state["query_type"] == "technical":
        return "tech_rag"
    else:
        return "general"
