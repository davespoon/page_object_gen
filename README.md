# pog (MVP skeleton)

Initial scaffolding for `pog`, a Python CLI that will generate C# Selenium Page Objects.

## Install (editable, recommended)

From repo root:

```bash
pip install -e tools/pog
```

or with pipx:

```bash
pipx install -e tools/pog
```

## Try it

```bash
pog --help
pog generate "https://example.com" CheckoutPage
```

Currently implemented:
- CLI parsing
- high-level logging
- `.sln` discovery by walking upward from current directory

Next slices will add Selenium capture, LangGraph graph, build/repair loop, etc.
