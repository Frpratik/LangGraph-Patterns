#=====================================================================
# PATTERN 1 - SEQUENTIAL
#=====================================================================
# idea      : one node finishes, then the next one starts
# nodes     : clean_node -> summary_node
# reads     : raw_ticket, clean_ticket
# writes    : clean_ticket, ticket_summary
# graph.py  : START -> clean -> summary
#
# the second node never calls the first one
# it only reads the state key the first node wrote, that is the link
#=====================================================================

from state import SupportState
from config import llm


def clean_node(state: SupportState) -> dict:
    """Stage 1: fixes typos and removes noise from the raw ticket."""

    prompt = (
        "You are a support ticket editor. Clean up the following customer message. "
        "Fix spelling and grammar, remove repeated words, keep every fact, number "
        "and order id exactly as written. Return only the cleaned message.\n\n"
        f"Message:\n{state['raw_ticket']}"
    )
    response = llm.invoke(prompt)

    return {"clean_ticket": response.content.strip()}


def summary_node(state: SupportState) -> dict:
    """Stage 2: turns the cleaned ticket into a one line summary for the agent."""

    prompt = (
        "Summarize this support ticket in ONE short sentence. Mention the problem "
        "and any order id. Return only the sentence.\n\n"
        f"Ticket:\n{state['clean_ticket']}"
    )
    response = llm.invoke(prompt)

    return {"ticket_summary": response.content.strip()}
