#=====================================================================
# ui.py - the terminal look of HelpHive (python main.py)
#=====================================================================
# only printing lives here, no graph logic
# main.py streams the graph and calls these functions for every step
# what a step means comes from describe.py, shared with the web page
#=====================================================================

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from describe import PATTERNS, NODE_PATTERN, SAMPLE_TICKETS, describe

console = Console()

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
        Text(describe(node, update), style="" if node == "reviewer" else "dim"),
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
