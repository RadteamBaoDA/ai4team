from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .config import load_config
from .summarizer import build_summary_engine
from .traversal import build_markdown, collect_structure
from .html_report import build_html_report, serialize_entries

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    default_config = repo_root / "structure_understand" / "config.yaml"
    parser = argparse.ArgumentParser(description="Generate a Markdown map of a folder tree with optional summaries.")
    parser.add_argument("-c", "--config", type=Path, default=default_config, help="path to the configuration YAML file")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    args = parse_arguments()
    config = load_config(args.config)
    summarizer = build_summary_engine(config.summarizer_settings)
    logger.info("Scanning %s", config.input_root)
    entries = collect_structure(config, summarizer)
    markdown = build_markdown(entries, config.input_root, config.config_path)
    config.output_file.parent.mkdir(parents=True, exist_ok=True)
    config.output_file.write_text(markdown, encoding="utf-8")
    logger.info("Structure report saved to %s", config.output_file)
    table_data = serialize_entries(entries)
    json_payload = json.dumps(table_data, ensure_ascii=False)
    config.json_output_file.parent.mkdir(parents=True, exist_ok=True)
    config.json_output_file.write_text(json_payload, encoding="utf-8")
    logger.info("JSON report saved to %s", config.json_output_file)
    html = build_html_report(entries, config.input_root, config.config_path, data_json=json_payload)
    config.html_output_file.parent.mkdir(parents=True, exist_ok=True)
    config.html_output_file.write_text(html, encoding="utf-8")
    logger.info("Interactive HTML report saved to %s", config.html_output_file)
