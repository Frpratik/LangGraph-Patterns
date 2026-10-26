#=====================================================================
# describe.py - what each node means, shared by both front ends
#=====================================================================
# ui.py (terminal) and server.py (web page) both show the same thing:
# "this node just finished, and this is what it did"
# keeping it here means the two front ends never disagree
#=====================================================================

#pattern number -> (name, terminal color)
PATTERNS = {
    1: ("SEQUENTIAL", "cyan"),
    2: ("PARALLEL + REDUCER", "magenta"),
    3: ("ROUTING", "yellow"),
    4: ("RAG", "green"),
    5: ("LOOP + TOOLS", "blue"),
    6: ("HUMAN IN THE LOOP", "red"),
}

#graph node name -> pattern number
NODE_PATTERN = {
    "clean": 1, "summary": 1,
    "sentiment": 2, "urgency": 2, "abuse": 2,
    "classifier": 3,
    "billing_rag": 4, "tech_rag": 4, "general": 4,
    "writer": 5, "tools": 5, "extract_draft": 5, "reviewer": 5,
    "human_review": 6,
}

SAMPLE_TICKETS = {
    "1": "hi i was charged twice for ORD-1003 plz fix fast!!",
    "2": "I cant login to my account, it says locked after I tried many times",
    "3": "thanks a lot, your team is great!",
}


def short(text, limit: int = 110) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 3] + "..."


def describe(node: str, update: dict) -> str:
    """One line that says what this node just did."""
    if node == "clean":
        return short(update["clean_ticket"])
    if node == "summary":
        return short(update["ticket_summary"])
    if node in ("sentiment", "urgency", "abuse"):
        name, value = next(iter(update["scores"].items()))
        return f"{name} = {value}/100"
    if node == "classifier":
        return f"category = {update['query_type']}"
    if node in ("billing_rag", "tech_rag"):
        return f"found {len(update['retrieved_context'])} characters of policy text"
    if node == "general":
        return "no documents needed"
    if node == "writer":
        last = update["messages"][-1]
        calls = getattr(last, "tool_calls", None)
        attempt = f"attempt {update['attempt']}: " if "attempt" in update else ""
        if calls:
            args = ", ".join(f"{k}={v!r}" for k, v in calls[0]["args"].items())
            return f"{attempt}asks for tool {calls[0]['name']}({args})"
        return f"{attempt}reply written"
    if node == "tools":
        return short(update["messages"][-1].content)
    if node == "extract_draft":
        return f"draft saved ({len(update['draft'])} characters)"
    if node == "reviewer":
        verdict = "APPROVED" if update["is_approved"] else "REJECTED"
        return f"{verdict} - {short(update['review_feedback'], 90)}"
    if node == "human_review":
        if update["status"] == "PENDING":
            return "asked for changes - back to the writer"
        return f"status = {update['status']}"
    return ""
