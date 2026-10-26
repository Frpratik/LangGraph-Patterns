# HelpHive Support Desk

A customer support desk that runs in your terminal, built to learn **6 core LangGraph patterns** in one working project.

A customer ticket goes in. The graph cleans it, scores it, routes it, looks up the right policy, drafts a reply, has an AI reviewer check it, and finally **pauses for a human to approve** before anything is sent.

```
$ python main.py

 HelpHive Support Desk
 P1 SEQUENTIAL   P2 PARALLEL + REDUCER   P3 ROUTING
 P4 RAG          P5 LOOP + TOOLS         P6 HUMAN IN THE LOOP

ticket > 1
```

---

## The 6 patterns, one file each

| # | Pattern | What it means | File |
|---|---------|---------------|------|
| 1 | **Sequential** | one node finishes, then the next starts | [`patterns/p1_sequential.py`](patterns/p1_sequential.py) |
| 2 | **Parallel + reducer** | independent nodes run together and write one shared key | [`patterns/p2_parallel.py`](patterns/p2_parallel.py) |
| 3 | **Conditional routing** | the graph picks its next node while running | [`patterns/p3_routing.py`](patterns/p3_routing.py) |
| 4 | **RAG** | fetch the right chunks of a PDF before answering | [`patterns/p4_rag.py`](patterns/p4_rag.py) |
| 5 | **Loop + tools** | write, review, rewrite until approved or out of tries | [`patterns/p5_loop_tools.py`](patterns/p5_loop_tools.py) |
| 6 | **Human in the loop** | the graph pauses for a person, then continues | [`patterns/p6_human_in_loop.py`](patterns/p6_human_in_loop.py) |

Every pattern file starts with a header that lists its nodes, the state keys it reads and writes, and the edges it adds in `graph.py`.

---

## How a ticket flows

```
 raw ticket
     |
     v
 [P1] clean ──> summary
                   |
        ┌──────────┼──────────┐
        v          v          v
 [P2] sentiment  urgency    abuse        (run in parallel, scores merged)
        └──────────┼──────────┘
                   v
 [P3]          classifier
                   |
        ┌──────────┼───────────┐
        v          v           v
 [P4] billing_rag tech_rag   general      (one route is chosen)
        └──────────┼───────────┘
                   v
 [P5]           writer <────────────┐
                 |   \              |
          tool?  |    └─> tools ────┘     (writer asks, ToolNode runs, result returns)
                 v
          extract_draft
                 |
                 v
              reviewer ── rejected ──> writer     (max 3 attempts)
                 |
              approved / max tries
                 v
 [P6]       human_review  ── feedback ──> writer  (max 2 rounds)
                 |
         approve |  or rejected twice
                 v
         SENT  /  ESCALATED
```

---

## Project structure

```
HelpHive-SupportDesk/
├── main.py                 run it - streams the graph into the terminal UI
├── ui.py                   terminal look (rich): banner, live steps, review panel
├── graph.py                wires every node and edge, compiles with a checkpointer
├── state.py                the shared state + the score reducer
├── config.py               models and limits
├── make_pdfs.py            creates the two PDFs in data/
├── data/
│   ├── billing_policy.pdf  knowledge for billing tickets
│   └── tech_faq.pdf        knowledge for technical tickets
└── patterns/
    ├── p1_sequential.py
    ├── p2_parallel.py
    ├── p3_routing.py
    ├── p4_rag.py
    ├── p5_loop_tools.py
    └── p6_human_in_loop.py
```

Read it in this order: `state.py` -> `patterns/p1` ... `p6` -> `graph.py` -> `main.py`.

---

## The state

`state.py` holds one shared notebook. Every node reads from it and returns only the keys it changes.

| Key | Written by | Pattern |
|-----|-----------|---------|
| `raw_ticket` | `main.py` | input |
| `clean_ticket`, `ticket_summary` | clean, summary | 1 |
| `scores` (`anger`, `urgency`, `abuse`) | three parallel nodes, merged by `merge_score_dicts` | 2 |
| `query_type` | classifier | 3 |
| `retrieved_context` | billing_rag / tech_rag / general | 4 |
| `messages`, `draft`, `review_feedback`, `is_approved`, `attempt` | writer, extract_draft, reviewer | 5 |
| `human_rounds`, `status`, `final_reply` | human_review | 6 |

---

## Setup

You need Python 3.10+ and a free [Groq API key](https://console.groq.com).

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

Create a `.env` file (copy `.env.example`):

```
GROQ_API_KEY=your_key_here
```

The two PDFs are already in `data/`. To regenerate them:

```bash
python make_pdfs.py
```

## Run

```bash
python main.py
```

Type `1`, `2` or `3` for a sample ticket, or write your own. Type `exit` to quit.

| Try this | What it shows |
|----------|---------------|
| `1` - charged twice on ORD-1003 | billing route, RAG, **tool call**, then your approval |
| `2` - locked out of the account | technical route, the tech FAQ |
| `3` - thanks, great team | general route, no documents |
| any ticket, then reply with feedback instead of `approve` | the human loop sends it back to the writer |
| reject twice | the ticket is **escalated** |

Order ids the tool knows: `ORD-1001`, `ORD-1002`, `ORD-1003`, `ORD-1004`.

### What you see

Each finished node prints a line, grouped under its pattern (illustrative output):

```
Pattern 1 - SEQUENTIAL ------------------------------------------
  done  clean          Hi, I was charged twice for ORD-1003. Please fix this quickly.
  done  summary        Customer was charged twice for order ORD-1003.
Pattern 2 - PARALLEL + REDUCER ----------------------------------
  done  sentiment      anger = 35/100
  done  urgency        urgency = 70/100
  done  abuse          abuse = 0/100
Pattern 3 - ROUTING ---------------------------------------------
  done  classifier     category = billing
Pattern 4 - RAG -------------------------------------------------
  done  billing_rag    found 1432 characters of policy text
Pattern 5 - LOOP + TOOLS ----------------------------------------
  done  writer         attempt 1: asks for tool lookup_order(order_id='ORD-1003')
  done  tools          Order ORD-1003: plan=Basic (monthly), status=Charged twice ...
  done  writer         reply written
  done  extract_draft  draft saved (412 characters)
  done  reviewer       APPROVED - Answers the question and ends with a next step.
Pattern 6 - HUMAN IN THE LOOP -----------------------------------
 Summary     Customer was charged twice for order ORD-1003.
 Category    billing
 Scores      anger=35  urgency=70  abuse=0
 AI reviewer approved

+-------------- Draft reply - waiting for you --------------+
| Sorry about the double charge ...                         |
+-----------------------------------------------------------+
Type 'approve' to send, or type your feedback to request a rewrite.
you >
```

---

## Configuration

Everything adjustable is in [`config.py`](config.py):

| Setting | Default | Meaning |
|---------|---------|---------|
| `llm`, `writer_llm` | Groq models | the reviewer/classifier model and the writer model |
| `MAX_ATTEMPTS` | 3 | writer tries before the draft goes to the human anyway |
| `MAX_HUMAN_ROUNDS` | 2 | times the human can reject before the ticket is escalated |

---

## Good to know

- **The checkpointer is in memory.** `MemorySaver` keeps paused tickets only while the program runs. A real deployment would use a database-backed checkpointer.
- **The order tool is a mock.** `lookup_order` reads a small dictionary in `p5_loop_tools.py`. Swap it for a real database or API call.
- **Tool calls depend on the model.** If a model produces a malformed tool call, run the ticket again.
- **First start is slower** because the embedding model loads and the PDFs are indexed.
