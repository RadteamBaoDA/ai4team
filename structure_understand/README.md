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
- `max_file_bytes`: how much of each file is read before summarization.
- `max_summary_chars`: placeholder summarizer fallback length.
- `summarizer.provider`: choose `placeholder`, `openai`, or `ollama`.
  - `openai.api_key_env` names the environment variable containing your key (default `OPENAI_API_KEY`).
  - For Ollama, point `ollama.url` at a running service (`http://localhost:11434/api/prompt` by default).
  - Swap providers or tweak the nested config without touching Python code.
- `summary_workers`: number of parallel worker threads that run summarization tasks, which defaults to the host CPU count; increase it for larger codebases to keep LLM requests in flight.

## Running
```bash
./run_structure_understand.sh [path/to/config.yaml]
```
```cmd
run_structure_understand.bat [path\to\config.yaml]
```
If you leave the argument off, the scripts default to `config.yaml` next to them. The scripts invoke `python -m structure_understand.cli`, so point `PYTHON_EXE` / `PYTHON_CMD` at a specific interpreter beforehand if needed.

The CLI resolves the configured `input_root`, traverses every folder/file, and writes a table to `output_file`. It logs progress to stdout so you can track what is being scanned.

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
