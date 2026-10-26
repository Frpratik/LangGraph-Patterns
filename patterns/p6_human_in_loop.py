#=====================================================================
# PATTERN 6 - HUMAN IN THE LOOP
#=====================================================================
# idea      : the graph pauses, a person decides, the graph continues
# node      : human_review_node
# router    : should_finish
# reads     : ticket_summary, query_type, scores, draft, is_approved, human_rounds
# writes    : status, final_reply, human_rounds, review_feedback, attempt
# graph.py  : human_review -> END | writer
#
# three things must exist for this to work
#   1. interrupt()                  pauses the graph (this file)
#   2. a checkpointer               saves the state (graph.py -> MemorySaver)
#   3. a thread_id                  names the save slot (main.py)
# the person answers with Command(resume=...) in main.py
#=====================================================================

from langgraph.types import interrupt
from langgraph.graph import END

from state import SupportState
from config import MAX_HUMAN_ROUNDS


def human_review_node(state: SupportState) -> dict:
    """Pauses and waits for the human agent to approve or give feedback."""

    #the graph freezes on this line and hands this dictionary to whoever called it
    #when the human answers, interrupt() returns their answer
    human_response = interrupt({
        "summary": state["ticket_summary"],
        "category": state["query_type"],
        "scores": state["scores"],
        "draft": state["draft"],
        "ai_approved": state["is_approved"],
        "instruction": "Type 'approve' to send, or type your feedback to request a rewrite.",
    })

    response = human_response.strip()
    rounds = state.get("human_rounds", 0) + 1

    #outcome 1 - approved
    if response.lower() in ["approve", "approved", "yes", "ok", "send"]:
        return {
            "status": "SENT",
            "final_reply": state["draft"],
            "human_rounds": rounds,
        }

    #outcome 2 - rejected too many times, escalate
    if rounds >= MAX_HUMAN_ROUNDS:
        return {
            "status": "ESCALATED",
            "final_reply": "",
            "human_rounds": rounds,
        }

    #outcome 3 - rejected, the writer gets a fresh set of attempts plus the human's feedback
    return {
        "status": "PENDING",
        "review_feedback": response,
        "is_approved": False,
        "attempt": 0,
        "human_rounds": rounds,
    }


def should_finish(state: SupportState):
    if state["status"] in ("SENT", "ESCALATED"):
        return END
    return "writer"
