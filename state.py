#the state is the shared notebook that every node reads from and writes to
#every graph starts with it so we write it first

from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


#reducer for the parallel branches (Pattern 2)
#three nodes write to the same key at the same time
#without a reducer langgraph raises an error, it allows only one write per key per step
#so we merge the small dicts into one

def merge_score_dicts(existing: dict, newupdate: dict) -> dict:
    if existing is None:
        return newupdate
    return {**existing, **newupdate}


class SupportState(TypedDict):
    #input
    raw_ticket: str

    #Pattern 1 - sequential intake
    clean_ticket: str
    ticket_summary: str

    #Pattern 2 - parallel scoring (sentiment, urgency, abuse)
    scores: Annotated[dict[str, int], merge_score_dicts]

    #Pattern 3 - routing
    query_type: str            # billing / technical / general

    #Pattern 4 - RAG
    retrieved_context: str

    #Pattern 5 - writer and reviewer loop (messages hold the tool calls)
    messages: Annotated[list, add_messages]
    draft: str
    review_feedback: str
    is_approved: bool
    attempt: int

    #Pattern 6 - human in the loop
    human_rounds: int
    status: str                # PENDING / SENT / ESCALATED
    final_reply: str
