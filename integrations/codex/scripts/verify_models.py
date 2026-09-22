"""Real checkpoint-selection and device smoke test; no downloads."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parents[1]))

from laya_codex_companion.runtime import Runtime  # noqa: E402

request = json.loads((ROOT / "examples/quickstart.json").read_text())
runtime = Runtime()
report = {"scope": "Real upstream checkpoint loads and routing; not broad accuracy evidence", "runs": [], "errors": []}
try:
    for model, state in [
        ("english", request["state"]),
        ("multilingual", "تم خصم المبلغ مرتين، أرجو إعادة المبلغ الزائد."),
        ("typed-decisions", request["state"]),
        ("auto", request["state"]),
        ("auto", "تم خصم المبلغ مرتين، أرجو إعادة المبلغ الزائد."),
    ]:
        try:
            result = runtime.predict(state, request["questions"], use_cache=False, model=model)
            selected = result["checkpoint"]["variant"]
            expected = ("english" if state == request["state"] else "multilingual") if model == "auto" else model
            if selected != expected:
                raise AssertionError(f"Expected {expected}, got {selected}")
            report["runs"].append({"requested": model, "result": result})
        except Exception as exc:
            report["errors"].append({"requested": model, "type": type(exc).__name__, "message": str(exc)})
    report["release"] = runtime.release()
finally:
    runtime.close()
output = ROOT / "evidence/windows-checkpoints.json"
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"runs": len(report["runs"]), "errors": report["errors"], "output": str(output)}, indent=2))
raise SystemExit(bool(report["errors"]))
