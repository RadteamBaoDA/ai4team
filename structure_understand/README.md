# Structure Understand

Structure-understand now lives under `src`, which keeps the implementation installable-ready and easier to maintain. A lightweight `structure_understand/app.py` bootstrapper exists so you can still run the CLI without installing the package.

## Setup
1. Activate your project environment (e.g., `source .venv/Scripts/activate`).
2. Install runtime dependencies listed in `structure_understand/requirements.txt`.

## Configuration
Edit `structure_understand/config.yaml` to control the scan and summarizer behavior:
- `input_root`: folder to inspect (relative to this config file or absolute).
- `output_file`: Markdown report destination, overwritten each run.
- `exclude_paths`: folder or file names to skip (case-sensitive).
  - `max_file_bytes`: how much of each file is read before summarization; leave blank to read the entire file.
  - `max_summary_chars`: placeholder summarizer fallback length.
  - `max_prompt_chars`: how much text is passed to the LLM; leave blank to send the full file.
  - `summary_type`: choose `placeholder`, `openai`, or `ollama`; defaults to `ollama` if not set.
  - `openai.api_key_env` names the environment variable containing your key (default `OPENAI_API_KEY`).
  - For Ollama, point `ollama.url` at a running service (`http://localhost:11434/api/prompt` by default).
  - Swap providers or tweak the nested config without touching Python code.
- `summary_extensions`: limits LLM summaries to files whose extensions match this list; omit the list to summarize every file.
- `html_output_file`: controls where the Tabler-powered interactive report is written.
- `summary_workers`: number of parallel worker threads that run summarization tasks, which defaults to the host CPU count; increase it for larger codebases to keep LLM requests in flight.
- `openai` and `ollama` integrations now use their own defaults for token counts, so you no longer need to configure `max_tokens` yourself.
  - The HTML report also renders a plain-text summary view after the table so you can read each file’s summary as unformatted text.

## File content handling
- The CLI extracts readable text from `.docx`, `.pptx`, `.xlsx`, and `.pdf` binaries before sending them to the summarizer, so your LLM always operates on full document contents rather than raw archives. PDF extraction relies on `PyPDF2` and gracefully falls back to the UTF-8 reader when the dependency is missing.
- After extraction, `max_file_bytes` still controls how much of the text is passed to the summarizer.

## Running
```bash
./run_structure_understand.sh [path/to/config.yaml]
```
```cmd
run_structure_understand.bat [path\to\config.yaml]
```
If you leave the argument off, the scripts default to `config.yaml` next to them. The scripts now run `structure_understand/app.py`, so point `PYTHON_EXE` / `PYTHON_CMD` at a specific interpreter beforehand if needed.

The CLI resolves the configured `input_root`, traverses every folder/file, and writes a table to `output_file`. It logs progress to stdout so you can track what is being scanned.

## Interactive HTML output
- The CLI emits an HTML version of the report (default next to the Markdown file) that uses the Tabler design system and a Tabulator-powered table.
- A sticky search input filters the table by path or summary text so you can quickly locate files or folders.
- The CLI also writes a `structure_summary.json` file (configurable via `json_output_file`) containing the same table data, letting other tooling consume the structural overview or powering the HTML report’s client-side table instead of embedding the dataset directly.

## Development
The code lives under `src`. When editing modules directly, run the CLI via the `uv` runner or by setting `PYTHONPATH=src`:

```bash
uv run python structure_understand/app.py
# or
PYTHONPATH=src python structure_understand/app.py
```

Both approaches ensure Python picks up the new `src` layout without installing the package.

## Output Format
The generated Markdown tables each path along with its kind, size, and the summary text. Folder rows describe children counts, while files show either placeholder heuristics or LLM-generated descriptions.
