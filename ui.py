#=====================================================================
# ui.py - the terminal look of HelpHive
#=====================================================================
# only printing lives here, no graph logic
# main.py streams the graph and calls these functions for every step
#=====================================================================

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console()

#pattern number -> (name, color)
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

_last_pattern = None


def banner():
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column()
    for number, (name, color) in PATTERNS.items():
        table.add_row(Text(f"P{number}  {name}", style=color))

    body = Text()
    body.append("Customer support desk built on 6 LangGraph patterns\n\n", style="bold")
    body.append("Paste a ticket. The AI drafts a reply, an AI reviewer checks it,\n")
    body.append("then YOU approve it before it is sent.\n")

    console.print(Panel(body, title="HelpHive Support Desk", border_style="bright_white", padding=(1, 2)))
    console.print(table)

    samples = Table(box=box.SIMPLE_HEAD, title="Quick start - type a number or write your own ticket")
    samples.add_column("Type", style="bold")
    samples.add_column("Ticket")
    for key, text in SAMPLE_TICKETS.items():
        samples.add_row(key, text)
    samples.add_row("exit", "quit the app")
    console.print(samples)


def ask_ticket():
    answer = console.input("\n[bold green]ticket >[/bold green] ").strip()
    return SAMPLE_TICKETS.get(answer, answer)


def new_ticket(ticket: str):
    global _last_pattern
    _last_pattern = None
    console.print()
    console.print(Panel(ticket, title="Incoming ticket", border_style="green"))


def _short(text: str, limit: int = 110) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 3] + "..."


def _describe(node: str, update: dict) -> str:
    """One line that says what this node just did."""
    if node == "clean":
        return _short(update["clean_ticket"])
    if node == "summary":
        return _short(update["ticket_summary"])
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
        return _short(update["messages"][-1].content)
    if node == "extract_draft":
        return f"draft saved ({len(update['draft'])} characters)"
    if node == "reviewer":
        verdict = "APPROVED" if update["is_approved"] else "REJECTED"
        return f"{verdict} - {_short(update['review_feedback'], 90)}"
    if node == "human_review":
        if update["status"] == "PENDING":
            return "asked for changes - back to the writer"
        return f"status = {update['status']}"
    return ""


def show_step(node: str, update: dict):
    """Prints one finished node. A new pattern gets its own header line."""
    global _last_pattern

    number = NODE_PATTERN.get(node)
    if number is None:
        return
    name, color = PATTERNS[number]

    if number != _last_pattern:
        console.print(Rule(f"Pattern {number} - {name}", style=color, align="left"))
        _last_pattern = number

    #a grid keeps wrapped text aligned under the detail column
    row = Table.grid(padding=(0, 1))
    row.add_column(no_wrap=True)
    row.add_column(no_wrap=True)
    row.add_column(ratio=1)
    row.add_row(
        Text("  done", style=f"bold {color}"),
        Text(node, style="bold"),
        Text(_describe(node, update), style="" if node == "reviewer" else "dim"),
    )
    console.print(row)


def show_review(data: dict):
    """The pause: shows everything the human needs to decide."""
    global _last_pattern
    name, color = PATTERNS[6]
    console.print(Rule(f"Pattern 6 - {name}", style=color, align="left"))
    _last_pattern = 6

    info = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    info.add_column(style="bold")
    info.add_column()
    info.add_row("Summary", data["summary"])
    info.add_row("Category", data["category"])
    info.add_row("Scores", "  ".join(f"{k}={v}" for k, v in data["scores"].items()))
    info.add_row("AI reviewer", "approved" if data["ai_approved"] else "not approved (max tries reached)")
    console.print(info)

    console.print(Panel(data["draft"], title="Draft reply - waiting for you", border_style=color, padding=(1, 2)))
    console.print(f"[dim]{data['instruction']}[/dim]")


def ask_human() -> str:
    return console.input("[bold red]you >[/bold red] ").strip()


def show_final(values: dict):
    console.print()
    if values.get("status") == "SENT":
        console.print(Panel(values["final_reply"], title="SENT to customer", border_style="green", padding=(1, 2)))
    else:
        console.print(Panel("Rejected twice. The ticket was handed to a senior agent.",
                            title="ESCALATED", border_style="red"))


def show_error(error: Exception):
    console.print(Panel(f"{type(error).__name__}: {error}", title="Something went wrong", border_style="red"))
    console.print("[dim]Check your GROQ_API_KEY in .env and try the ticket again.[/dim]")
