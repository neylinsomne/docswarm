# Concepts & vocabulary

A short glossary of the terms docswarm uses. Understanding these five is enough
to use the whole engine.

### Plan
The configuration that drives a document run: its sections, which agent writes
each, in what order, and the anti-overlap rules. It is the **only** place a
domain is expressed. Loaded from YAML/JSON or built as a dict. See
`docswarm.config.PlanConfig`.

### Contract (`SectionContract`)
What the orchestrator hands each agent. Two jobs:
- **Anti-overlap**: `must_cover` / `must_not_cover` give each section a *disjoint
  scope*, so two agents can't write the same thing.
- **Complementarity**: `produces` / `consumes` *anchors* — section A produces a
  table; section B is told to cite it.

The contract renders to a text block prepended to the agent's prompt.

### Anchor
A citable symbol (a table or figure) with a stable `anchor_id`. The producer
publishes it to the blackboard with a short **summary** (e.g. "table 3 rows × 2
cols"); a consumer cites it with the marker `[ref:anchor_id]`. The consumer
never receives the producer's full content — only the summary and the id.

### Blackboard
A shared, in-memory board (Hearsay-II pattern). It holds the run's **facts**
(authoritative shared data — same names/dates everywhere) and the published
**anchors**. Agents coordinate *only* through it; they never call each other.
This stigmergic style is why they complement without overlapping.

### Late binding (in the composer)
The composer assembles all sections first, then — *late* — numbers tables and
resolves `[ref:...]` into "Table N". Because numbering happens after placement,
agents can run in any order (or in parallel) and the cross-references still
resolve correctly. No LLM is involved in assembly; it is fully deterministic.

---

### A picture of one run

```
plan ──▶ contracts ──┐
facts ──▶ blackboard ─┤
                      ▼
   section A (agent: tabulator)               section B (agent: analyst)
   contract: produces tbl-metrics             contract: consumes tbl-metrics
   writes a table ──▶ publishes anchor ──────▶ reads summary, cites [ref:tbl-metrics]
                      (to blackboard)
                      │                                    │
                      └──────────▶ composer ◀──────────────┘
                                   numbers tbl-metrics = "Table 1"
                                   resolves [ref:tbl-metrics] → "Table 1"
                                   ▼
                              document_v1 (markdown + html)
```
