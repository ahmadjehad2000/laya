"""Render comparable tables from completed benchmark reports; never invent missing results."""
import argparse
import json
from pathlib import Path
import statistics


def tables(paths):
    reports = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    for report in reports:
        if report["errors"] or not report.get("release_verified"):
            raise ValueError("Only completed reports without harness errors can be summarized")
        if report["ag_news"]["errors"] or report["rubric"]["metrics"]["errors"] or any(g["record_errors"] for g in report["synthetic"]["groups"]):
            raise ValueError("Resolve or explicitly document record errors before publishing comparison tables")
    # Comparison requires matching fixture selection, questions, model and run counts.
    first = reports[0]
    for report in reports[1:]:
        for key in ("sha256", "seed", "per_class", "questions"):
            if report["ag_news"][key] != first["ag_news"][key]:
                raise ValueError(f"Noncomparable AG News {key}")
        if report["checkpoint"] != first["checkpoint"]:
            raise ValueError("Compare one pinned checkpoint per table")
        for key in ("samples", "cold_runs", "warmup", "batch_repeats"):
            if report["settings"][key] != first["settings"][key]:
                raise ValueError(f"Noncomparable measurement setting: {key}")
    labels = []
    for report in reports:
        system = report["host"]["platform"]
        name = "Debian WSL2" if "microsoft" in system.lower() else ("Windows" if system.startswith("Windows") else "Linux" if system.startswith("Linux") else "macOS")
        labels.append(name + " " + report["actual_device"].upper())
    lines = ["| Measurement | " + " | ".join(labels) + " |", "| :--- | " + " | ".join(["---:"] * len(labels)) + " |"]
    def row(label, values):
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    row("AG News subset accuracy", [f"{r['ag_news']['metrics']['correct']}/{r['ag_news']['metrics']['n']} ({r['ag_news']['metrics']['accuracy']:.1%})" for r in reports])
    row("AG News macro-F1", [f"{r['ag_news']['metrics']['macro_f1']:.4f}" for r in reports])
    row("Synthetic workflow decisions", [f"{sum(g['correct'] for g in r['synthetic']['groups'])}/{sum(g['total'] for g in r['synthetic']['groups'])}" for r in reports])
    row("Synthetic rubric rounded accuracy", [f"{r['rubric']['metrics']['rounded_correct']}/{r['rubric']['metrics']['n']}" for r in reports])
    row("Rubric MAE (0–3 index; lower is better)", [f"{r['rubric']['metrics']['mae_valid']:.3f}" for r in reports])
    row(f"Fresh server init + first request, median ({first['settings']['cold_runs']} runs)", [f"{statistics.median(x['total_ms'] for x in r['cold_processes'])/1000:.2f} s" for r in reports])
    for tier in ("short", "medium", "long"):
        row(f"Warm {tier} MCP request, p50 / p95", [f"{r['performance'][tier]['client']['p50_ms']:.1f} / {r['performance'][tier]['client']['p95_ms']:.1f} ms" for r in reports])
    row("Exact cache hit, p50", [f"{r['performance']['cache_hit']['client']['p50_ms']:.2f} ms" for r in reports])
    row("8-record batch throughput", [f"{r['performance']['batch_8']['records_per_second']:.1f} records/s" for r in reports])
    row("Three related questions, p50", [f"{r['performance']['three_questions']['client']['p50_ms']:.1f} ms" for r in reports])
    row("Resident server RSS snapshot (not peak)", [f"{r['resident_status']['process_rss_mib']/1024:.2f} GiB" for r in reports])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = tables(args.reports)
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result)
