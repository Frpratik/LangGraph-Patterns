#=====================================================================
# PATTERN 2 - PARALLEL FAN-OUT + REDUCER
#=====================================================================
# idea      : independent jobs run at the same time
# nodes     : sentiment_node, urgency_node, abuse_node
# reads     : clean_ticket
# writes    : scores  (all three nodes write the SAME key)
# graph.py  : summary -> [sentiment, urgency, abuse] -> classifier
#
# because three nodes write one key in the same step, that key needs a
# reducer, see merge_score_dicts in state.py
# the list form of add_edge makes the classifier wait for all three
#=====================================================================

import re
from state import SupportState
from config import llm


def get_score(prompt: str) -> int:
    """Asks the llm for a number from 0 to 100, and falls back to 0 if the answer is not a number."""
    response = llm.invoke(prompt)
    match = re.search(r"\d+", response.content)
    if not match:
        return 0
    return min(int(match.group()), 100)


def sentiment_node(state: SupportState) -> dict:
    """Branch 1: how angry is the customer."""
    prompt = (
        "Rate how ANGRY or frustrated the customer is in this ticket from 0 to 100. "
        "0 means calm and polite, 100 means furious. "
        "Return ONLY the integer, nothing else.\n\n"
        f"Ticket:\n{state['clean_ticket']}"
    )
    return {"scores": {"anger": get_score(prompt)}}


def urgency_node(state: SupportState) -> dict:
    """Branch 2: how urgent is the ticket."""
    prompt = (
        "Rate how URGENT this ticket is from 0 to 100. 0 means no hurry, 100 means "
        "the customer cannot work or money is at risk right now. "
        "Return ONLY the integer, nothing else.\n\n"
        f"Ticket:\n{state['clean_ticket']}"
    )
    return {"scores": {"urgency": get_score(prompt)}}


def abuse_node(state: SupportState) -> dict:
    """Branch 3: is the ticket abusive or spam."""
    prompt = (
        "Rate how much this ticket contains abuse, threats, or spam from 0 to 100. "
        "0 means a normal message, 100 means pure abuse or spam. "
        "Return ONLY the integer, nothing else.\n\n"
        f"Ticket:\n{state['clean_ticket']}"
    )
    return {"scores": {"abuse": get_score(prompt)}}
