# Contributing to docswarm

Thanks for your interest! docswarm is a small, focused engine — contributions
that keep it that way are very welcome.

## Ground rules

1. **The engine core stays dependency-free.** `docswarm.orchestration`,
   `docswarm.ports`, `docswarm.agents`, `docswarm.config`, `docswarm.runner` must
   import nothing outside the standard library. Heavy deps belong in
   `extractors/` or `adapters/`, lazily imported, and declared as optional
   extras in `pyproject.toml`.
2. **The composer is deterministic.** No LLM calls, randomness, or wall-clock in
   `orchestration/`. Same input → same output.
3. **No domain leaks.** Anything specific to a use case goes in a plan (config)
   or an agent's system prompt — never in engine code.
4. **Tests run offline.** Use `StubLLM`; never require a network or a model in
   the suite.

## Dev setup

```bash
python -m venv .venv && . .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[yaml,dev,ingest]"
pytest -q
python -m examples.informe_demo.run            # sanity check the swarm
```

## Submitting

- Keep PRs small and focused; describe the *why*.
- Add or update tests for any behavior change.
- Match the surrounding style (concise docstrings explaining intent, not syntax).

## License of contributions

By contributing you agree your contribution is licensed under the project's
[PolyForm Noncommercial 1.0.0](LICENSE) license.
