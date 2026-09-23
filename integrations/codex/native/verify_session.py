"""Installed worker and opt-in real Astra/Sol context pilot. Uses normal Codex auth."""
import argparse, hashlib, json, os, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
from laya_codex_companion.config import home
from laya_codex_companion.compaction import compact_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true", help="Also call real Astra/Sol; consumes normal provider usage")
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    root = home()/"native"
    binary = root/json.loads((root/"build.json").read_text())["package"]/"bin/codex.exe"
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "scope":"Synthetic single-task pairs, not general savings or model accuracy", "runs":[]}
    reqs=[]
    for model in ["gpt-6-astra","gpt-6-sol"]:
     for i in range(2):
      reqs.append({"protocol":1,"id":model+str(i),"generation":i+1,"model":model,"milestones":True,"supported_efforts":["low","medium","high","xhigh"],"evidence":{"requests":["Inspect this test record. Do not deploy. "*500],"recent":["Tests failed; verify source."]}})
    p=subprocess.run([sys.executable,"-I","-m","laya_codex_companion.controller"], input="".join(json.dumps(r)+"\n" for r in reqs),text=True,capture_output=True,encoding="utf-8",timeout=240)
    replies=[json.loads(x) for x in p.stdout.splitlines()]
    report["overflow_worker"] = replies
    report["overflow_passed"] = len(replies)==4 and all(r["status"]=="decided" for r in replies)
    (out/"session-pilot.json").write_text(json.dumps(report,indent=2))
    if not report["overflow_passed"]: raise SystemExit("Worker failed; see report")
    if not args.live:
     return 0
    with tempfile.TemporaryDirectory(prefix="laya-session-pilot-") as temp:
     work=Path(temp)
     messages=[{"role":"user","content":"Never deploy. Goal: report unresolved tests."},{"role":"tool","content":"Successful inventory record, no action needed. "*1000},{"role":"user","content":"Unresolved tests: AUTH-17. Report the restriction and unresolved ID. No tools."}]
     raw=json.dumps(messages); (work/"chat.json").write_text(raw)
     handoff=compact_file(work,"chat.json",keep_recent=1)
     compact=Path(handoff["context"]).read_text()
     report["handoff"]= {k:v for k,v in handoff.items() if k not in ("context","archive")}
     for model in ["laya-astra","laya-sol"]:
      for arm,context in [("full",raw),("handoff",compact)]:
       logs=work/(model+arm); start=time.perf_counter()
       env={**os.environ,"LAYA_CONTROLLER_PYTHON":sys.executable,"LAYA_CONTROLLER_LOG_DIR":str(logs),"LAYA_ENFORCE":"1"}
       cmd=[str(binary),"--enable","step_model_switching","--enable","reasoning_effort_override","exec","--ignore-user-config","--ephemeral","--json","--skip-git-repo-check","-s","read-only","-C",str(work),"-m",model,"-"]
       prompt="Without tools, read this historical data and output only the deployment restriction and unresolved test ID.\n"+context
       try:
        p=subprocess.run(cmd,input=prompt,text=True,capture_output=True,encoding="utf-8",env=env,timeout=240)
        events=[json.loads(x) for x in p.stdout.splitlines() if x.startswith("{")]
        usage=next((e["usage"] for e in events if e.get("type")=="turn.completed"),None)
        answer=" ".join(e["item"].get("text","") for e in events if e.get("type")=="item.completed")
        row={"model":model,"arm":arm,"returncode":p.returncode,"elapsed_seconds":time.perf_counter()-start,"usage":usage,"correct": "AUTH-17" in answer and ("never deploy" in answer.lower() or "do not deploy" in answer.lower()),"answer":answer,"stats_emitted":"Laya task stats:" in p.stdout+p.stderr}
        if p.returncode: row["error"]=(p.stdout+p.stderr)[-2500:]
       except subprocess.TimeoutExpired: row={"model":model,"arm":arm,"error":"timeout","correct":False}
       report["runs"].append(row); (out/"session-pilot.json").write_text(json.dumps(report,indent=2)); print(json.dumps(row),flush=True)
    
    if not all(r.get("returncode") == 0 and r.get("correct") and r.get("stats_emitted") and r.get("usage") for r in report["runs"]):
        raise SystemExit("Live session verification failed; inspect session-pilot.json")


if __name__ == "__main__":
    raise SystemExit(main())
