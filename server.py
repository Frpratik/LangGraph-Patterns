#=====================================================================
# server.py - the web front end of HelpHive
#=====================================================================
# python server.py   ->   opens http://127.0.0.1:8000
#
# the page (static/index.html) talks to two endpoints:
#   POST /api/run     starts a ticket
#   POST /api/resume  sends the human's answer to a paused ticket (pattern 6)
#
# both answer with a STREAM of json lines, one per event, so the page can
# draw every node the moment it finishes:
#   {"type": "start",  "thread_id": ...}
#   {"type": "step",   "node": ..., "pattern": 1-6, "name": ..., "detail": ...}
#   {"type": "pause",  "data": {...}}              graph is waiting for the human
#   {"type": "done",   "status": ..., "reply": ...}
#   {"type": "error",  "message": ...}
#=====================================================================

import json
import os
import threading
import uuid
import webbrowser

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from langgraph.types import Command

from graph import app as support_graph
from state import new_state
from describe import PATTERNS, NODE_PATTERN, SAMPLE_TICKETS, describe

api = FastAPI(title="HelpHive Support Desk")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
MAX_TICKET_CHARS = 2000


class RunBody(BaseModel):
    ticket: str


class ResumeBody(BaseModel):
    thread_id: str
    answer: str


def event(**fields) -> str:
    return json.dumps(fields) + "\n"


def stream_graph(payload, config, thread_id: str):
    """Runs the graph and yields one json line per event."""
    yield event(type="start", thread_id=thread_id)

    try:
        paused = False
        for chunk in support_graph.stream(payload, config=config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    paused = True
                    yield event(type="pause", data=update[0].value)
                    continue

                number = NODE_PATTERN.get(node)
                if number is None:
                    continue
                yield event(
                    type="step",
                    node=node,
                    pattern=number,
                    name=PATTERNS[number][0],
                    detail=describe(node, update),
                )

        if not paused:
            values = support_graph.get_state(config).values
            yield event(type="done", status=values.get("status"), reply=values.get("final_reply", ""))

    except Exception as error:
        yield event(type="error", message=f"{type(error).__name__}: {error}")


def ndjson(generator) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api.get("/api/meta")
def meta():
    return {
        "patterns": [{"n": n, "name": name} for n, (name, _) in PATTERNS.items()],
        "samples": SAMPLE_TICKETS,
    }


@api.post("/api/run")
def run(body: RunBody):
    ticket = body.ticket.strip()[:MAX_TICKET_CHARS]
    thread_id = str(uuid.uuid4())

    if not ticket:
        return ndjson(iter([event(type="error", message="The ticket is empty.")]))

    #every ticket gets its own thread id so the pause and resume stay separate
    config = {"configurable": {"thread_id": thread_id}}
    return ndjson(stream_graph(new_state(ticket), config, thread_id))


@api.post("/api/resume")
def resume(body: ResumeBody):
    config = {"configurable": {"thread_id": body.thread_id}}

    #a thread id we never saw has no saved state to continue
    if not support_graph.get_state(config).values:
        return ndjson(iter([event(type="error", message="This ticket has expired. Start a new one.")]))

    return ndjson(stream_graph(Command(resume=body.answer.strip()), config, body.thread_id))


@api.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn

    url = "http://127.0.0.1:8000"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"HelpHive is running at {url}  (Ctrl+C to stop)")
    uvicorn.run(api, host="127.0.0.1", port=8000, log_level="warning")
