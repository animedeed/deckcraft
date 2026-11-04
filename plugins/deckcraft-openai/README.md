# Deckcraft — Codex and ChatGPT Work

PowerPoint with Morph/native animations and interactive HTML from shared scenes. Includes visual briefs, configurable HTML toolbar, build/remix/review and content/motion checks.

Uses a hosted or local Python code environment. Includes no desktop-only execution requirement. ChatGPT web/mobile requires Work, account installation and code execution; publishing on GitHub alone does not provide these. See [RUNTIME.md](RUNTIME.md) for runtime discovery, dependencies and checks. The public repository contains the separate original Claude package.

Install from the repository marketplace:

```text
codex plugin marketplace add animedeed/deckcraft --ref main
codex plugin add deckcraft@deckcraft
```

Python 3.10+ is required. In a compatible environment, run `python scripts/check_environment.py`. Missing libraries can be installed into a virtual environment with `python -m pip install -r requirements.txt`. Browser checks additionally require Playwright and a Chromium browser. No dependencies or lifecycle hooks are run automatically when the plugin loads.
