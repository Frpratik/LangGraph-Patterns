#=====================================================================
# main.py - runs the support desk in the terminal
#=====================================================================
# python main.py
#
# app.stream(..., stream_mode="updates") gives us every node the moment it
# finishes, that is how the terminal shows the pipeline live
#
# pattern 6 lives here too:
#   - the stream ends early when the graph hits interrupt()
#   - Command(resume=answer) with the SAME thread_id continues it
#=====================================================================

import uuid
from langgraph.types import Command

from graph import app
import ui


def run_graph(payload, config):
    """Runs the graph until it finishes or pauses. Returns the pause data, or None if finished."""
    pause_data = None

    with ui.console.status("[dim]working...[/dim]", spinner="dots"):
        for chunk in app.stream(payload, config=config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    pause_data = update[0].value
                else:
                    ui.show_step(node, update)

    return pause_data


def new_state(ticket: str) -> dict:
    return {
        "raw_ticket": ticket,
        "scores": {},
        "messages": [],
        "draft": "",
        "review_feedback": "",
        "is_approved": False,
        "attempt": 0,
        "human_rounds": 0,
        "status": "PENDING",
        "final_reply": "",
    }


def main():
    ui.banner()

    while True:
        try:
            ticket = ui.ask_ticket()
        except (KeyboardInterrupt, EOFError):
            break

        if ticket.lower() in ["exit", "quit"]:
            break
        if not ticket:
            continue

        ui.new_ticket(ticket)

        #every ticket gets its own thread id so the pause and resume stay separate
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}

        try:
            pause_data = run_graph(new_state(ticket), config)

            #while the graph is paused, show the draft and wait for the human
            while pause_data is not None:
                ui.show_review(pause_data)
                answer = ui.ask_human()
                pause_data = run_graph(Command(resume=answer), config)

            ui.show_final(app.get_state(config).values)

        except KeyboardInterrupt:
            break
        except Exception as error:
            ui.show_error(error)

    ui.console.print("\n[dim]Bye.[/dim]")


if __name__ == "__main__":
    main()
