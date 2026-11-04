# Deckcraft for Codex and ChatGPT Work

This skills-only package uses a Python code environment, either hosted or local. It has no local MCP server, desktop-only hooks, COM build dependency or machine-specific paths. Web and mobile clients can start cloud work where ChatGPT Work, this plugin and code execution are available. Installing the repository in Codex does not install it into a ChatGPT account, and does not add a code executor to ordinary Chat. The original Claude package is separate, at `plugins/deckcraft` in the source repository.

Use morphkit for Deckcraft, PowerPoint Morph/native animations and the corresponding HTML scenes. Preserve supplied artwork, editability and requested interactions. Do not flatten a deck to images just to change authoring tools.

## Find a Python runtime

Use Python 3.10+ with `python-pptx`, `lxml`, Pillow, numpy and shapely. Prefer an existing compatible environment. If `DECKCRAFT_PYTHON` is set, use that interpreter; otherwise inspect the host-provided runtime and the project's virtual environment. A `python` command on Windows can be a nonfunctional Store alias. Use an absolute interpreter path when necessary.

Run `<python> scripts/check_environment.py` from this plugin root before building. It reports required packages, versions and optional tools without installing anything. Missing dependencies produce a clear nonzero exit. Install into an isolated environment only when authorized; never modify the host's bundled runtime. The engine's dependencies are listed in `requirements.txt`; Playwright and a browser are optional for web QA.

Set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` for Windows commands. Resolve `skills/pptx-morph/scripts` from this installed plugin root and add its absolute path to `sys.path`/`PYTHONPATH`, or use it as the command working directory. Write generated decks, briefs, preview assets and reports in the task workspace, outside the plugin cache.

## Optional checks

- `DECKCRAFT_XSD_DIR`: an OOXML schema directory containing `pml.xsd` and its dependencies. Use `xsd_available()` before `xsd_check(file, required=True)`. Missing schemas mean skipped; an invalid explicit path is an error. Schemas are not redistributed in this package.
- `DECKCRAFT_SOFFICE`: absolute LibreOffice executable path; otherwise the engine searches PATH and standard Windows installation directories. Its render/effects import checks do not prove actual PowerPoint Morph playback.
- `DECKCRAFT_PDFTOPPM`: optional absolute Poppler `pdftoppm` path.
- `DECKCRAFT_CHROME`: optional Chromium/Chrome executable for Playwright. Reuse an installed browser when possible; an additional browser download is not required.
- On Windows with PowerPoint installed, `scripts/render_powerpoint.ps1 -InputPath <deck.pptx> -OutputDirectory <work/png>` reads the presentation without saving changes and exports static frames. Real slideshow playback still needs visual review.

## Visual brief and HTML controls

The brief and comparison pages run in a browser. Save downloads JSON and retains a browser-local copy. Read the user-supplied JSON file/path or pasted JSON; the chat cannot automatically see localStorage. Keep all assets listed in `publish.json` beside a brief/comparison page. The final presentation HTML is a standalone file.

Offer full controls or a custom toolbar for HTML. By default retain notes, overview, presenter view, annotations/pen, laser pointer, print/PDF, paging, full screen and help. Save the selection in `brief.json.show_ui`, then pass it unchanged as `ui` to the exporter. PDF uses browser print and is static. Notes and the presenter window need actual per-slide notes. Keep the `ui` module in all HTML presentations.

## Install from GitHub

```text
codex plugin marketplace add animedeed/deckcraft --ref main
codex plugin add deckcraft@deckcraft
```

Start a new chat after installation. This installs in Codex; it is separate from ChatGPT account installation and the public OpenAI Directory. No automatic lifecycle hooks run, and there is no automatic dependency installation or update check.

## Cloud, web and phone

Use the code environment attached to the current Work chat; Python and the files run on the host, not on the phone. Find the mounted plugin root and use its bundled morphkit exactly as in local builds. Read attached files from the host's attachment paths. A Windows path from another device is not an uploaded file: ask for the attachment if it is absent. Do not depend on PowerPoint COM or a local browser for building. Missing optional rendering tools mean a skipped check, never a claimed pass. Return artifacts using the host's downloadable-file mechanism.

For a small-screen or cloud chat, collect the brief and toolbar choices directly in chat unless the user wants the visual survey. Keep the final HTML standalone; it must not require local files, network access or installation. Use tap navigation as well as keyboard controls. A browser fullscreen or presenter-popup restriction is not a build failure; document it when observed.

The GitHub marketplace is not a public ChatGPT listing. To distribute there, package this directory as ZIP and follow https://developers.openai.com/plugins/deploy/submission (Skills only). This requires a verified publishing identity and review. Until installed in the account, do not claim web/mobile availability. If the current surface cannot load skills or execute Python, explain that limitation instead of inventing a successful build. A remote MCP deployment is a separate option, not included in this skills-only package.
