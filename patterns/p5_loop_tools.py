#=====================================================================
# PATTERN 5 - LOOP WITH EXIT CONDITION + TOOL CALLING
#=====================================================================
# idea      : write, check, rewrite, until good enough or out of tries
# nodes     : writer_node, tool_node, extract_draft_node, reviewer_node
# routers   : should_use_tool, should_stop_looping
# reads     : clean_ticket, ticket_summary, scores, retrieved_context
# writes    : messages, attempt, draft, review_feedback, is_approved
#
# graph.py  : writer -> tools -> writer              (tool loop)
#             writer -> extract_draft -> reviewer
#             reviewer -> writer                     (rewrite loop)
#             reviewer -> human_review               (approved or max tries)
#
# part 1 - the tool the writer may call
# part 2 - the writer, with both of its modes
# part 3 - the reviewer
# part 4 - the two router functions (the exit conditions)
#=====================================================================

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import ToolNode

from state import SupportState
from config import llm, writer_llm, MAX_ATTEMPTS


#---------------------------------------------------------------------
# part 1 - the tool
# a fake order table is enough for learning, in real life this is a database or an api
#---------------------------------------------------------------------

ORDERS = {
    "ORD-1001": {"plan": "Pro (monthly)", "amount": 999, "status": "Paid", "purchased_days_ago": 3},
    "ORD-1002": {"plan": "Business (annual)", "amount": 24990, "status": "Paid", "purchased_days_ago": 40},
    "ORD-1003": {"plan": "Basic (monthly)", "amount": 499, "status": "Charged twice", "purchased_days_ago": 1},
    "ORD-1004": {"plan": "Pro (monthly)", "amount": 999, "status": "Payment failed", "purchased_days_ago": 6},
}


@tool
def lookup_order(order_id: str) -> str:
    """Look up an order by its id (like ORD-1001). Returns plan, amount, status and how many days ago it was bought."""
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        return f"No order found with id {order_id}."
    return (
        f"Order {order_id.upper()}: plan={order['plan']}, amount=Rs {order['amount']}, "
        f"status={order['status']}, purchased {order['purchased_days_ago']} days ago."
    )


tools = [lookup_order]

#bind_tools lets the llm ASK for a tool, the llm never runs it
#ToolNode is the graph node that actually runs the requested tool
writer_llm_with_tools = writer_llm.bind_tools(tools)
tool_node = ToolNode(tools)


#---------------------------------------------------------------------
# part 2 - the writer
#---------------------------------------------------------------------

WRITER_SYSTEM_PROMPT = (
    "You are a friendly, professional customer support agent for HiveBoard, a "
    "project management app. Write the reply that will be sent to the customer. "
    "Rules: use ONLY the policy context given, never invent policies or numbers, "
    "if the customer mentions an order id use the lookup_order tool to check it "
    "before answering, be empathetic if the customer is upset, keep it under 150 "
    "words, and end with one clear next step. "
    "If you receive feedback on a previous draft, fix every point."
)


def writer_node(state: SupportState) -> dict:
    """Writes (or rewrites) the reply. Can call lookup_order first."""

    messages = state.get("messages", [])
    last = messages[-1] if messages else None

    #mode B - we are coming back from the tool node, same attempt, continue the same chat
    if isinstance(last, ToolMessage):
        response = writer_llm_with_tools.invoke([("system", WRITER_SYSTEM_PROMPT)] + messages)
        return {"messages": [response]}

    #mode A - a fresh attempt
    attempt = state.get("attempt", 0) + 1
    feedback = state.get("review_feedback", "")

    user_message = (
        f"Customer ticket:\n{state['clean_ticket']}\n\n"
        f"Ticket summary: {state['ticket_summary']}\n"
        f"Customer anger score: {state['scores'].get('anger', 0)}/100\n\n"
        f"Policy context:\n{state['retrieved_context']}\n\n"
    )
    if feedback:
        user_message += (
            f"Your previous draft was rejected.\n"
            f"Previous draft:\n{state['draft']}\n\n"
            f"Feedback:\n{feedback}\n\n"
            f"Write a NEW improved reply that fixes every point."
        )
    else:
        user_message += "Write the reply to the customer."

    human_message = HumanMessage(content=user_message)
    response = writer_llm_with_tools.invoke([("system", WRITER_SYSTEM_PROMPT), human_message])

    #REMOVE_ALL clears the old attempt's chat so each attempt starts clean
    return {
        "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), human_message, response],
        "attempt": attempt,
    }


def extract_draft_node(state: SupportState) -> dict:
    """After the writer is done with tools, pulls the final text out as the draft."""
    return {"draft": state["messages"][-1].content}


#---------------------------------------------------------------------
# part 3 - the reviewer
#---------------------------------------------------------------------

REVIEWER_SYSTEM_PROMPT = (
    "You are a strict support quality reviewer. Judge whether a reply is ready "
    "to send to the customer. Check:\n"
    "1. It actually answers the customer's question\n"
    "2. It only uses facts from the policy context or the order lookup (nothing invented)\n"
    "3. Polite and empathetic tone, calm if the customer is angry\n"
    "4. Under about 150 words\n"
    "5. Ends with one clear next step\n\n"
    "Respond in exactly this format:\n"
    "VERDICT: APPROVED or REJECTED\n"
    "FEEDBACK: <one short paragraph>\n\n"
    "Approve only if every point is met."
)


def reviewer_node(state: SupportState) -> dict:
    """Reviews the draft and decides: approve or reject with feedback."""

    prompt = (
        f"Customer ticket:\n{state['clean_ticket']}\n\n"
        f"Policy context:\n{state['retrieved_context']}\n\n"
        f"Draft reply:\n{state['draft']}\n\n"
        "Give your review."
    )
    response = llm.invoke([("system", REVIEWER_SYSTEM_PROMPT), ("human", prompt)])
    review_text = response.content.strip()

    #the verdict is the text before the word FEEDBACK
    verdict_line = review_text.upper().split("FEEDBACK")[0]
    is_approved = "APPROVED" in verdict_line and "REJECTED" not in verdict_line

    if "FEEDBACK:" in review_text:
        feedback = review_text.split("FEEDBACK:", 1)[1].strip()
    else:
        feedback = review_text

    return {"review_feedback": feedback, "is_approved": is_approved}


#---------------------------------------------------------------------
# part 4 - the routers (the exit conditions)
#---------------------------------------------------------------------

def should_use_tool(state: SupportState):
    last_message = state["messages"][-1]
    tool_calls_so_far = sum(1 for m in state["messages"] if isinstance(m, ToolMessage))

    #safety stop so the writer can't call tools forever
    if getattr(last_message, "tool_calls", None) and tool_calls_so_far < 3:
        return "tools"
    return "extract_draft"


def should_stop_looping(state: SupportState):
    if state["is_approved"]:
        return "human_review"
    if state["attempt"] >= MAX_ATTEMPTS:
        return "human_review"
    return "writer"
