import json


def bounded_json(value, limit):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > limit:
        raise ValueError(f"Request exceeds {limit} bytes; split into smaller batches")
    return raw


def questions_check(questions, config):
    if not isinstance(questions, dict) or not 1 <= len(questions) <= config.max_questions:
        raise ValueError(f"Supply 1–{config.max_questions} questions keyed by unique ID")
    bounded_json(questions, config.max_request_bytes)
    for qid, q in questions.items():
        if not isinstance(qid, str) or not 1 <= len(qid) <= 80 or not isinstance(q, dict):
            raise ValueError("Question IDs must be 1–80 characters and definitions must be objects")
        if set(q) - {"type", "instructions", "criteria"}:
            raise ValueError(f"Unknown question field in {qid}")
        if q.get("type") not in ("choice", "score", "noul"):
            raise ValueError(f"Invalid question type in {qid}")
        if not isinstance(q.get("instructions"), str) or not q["instructions"].strip():
            raise ValueError(f"{qid} needs nonempty instructions")
        criteria = q.get("criteria")
        if q["type"] in ("choice", "score"):
            if not isinstance(criteria, (dict, list)) or not 2 <= len(criteria) <= 16:
                raise ValueError(f"{qid} needs 2–16 criteria")
            if q["type"] == "score" and not isinstance(criteria, list):
                raise ValueError("Score criteria must be an ordered list")
            if q["type"] == "choice":
                labels = list(criteria)
                if not all(isinstance(x, str) and x.strip() for x in labels):
                    raise ValueError("Choice labels must be nonempty strings")
                if len(set(labels)) != len(labels):
                    raise ValueError("Choice labels must be unique")
        elif criteria is not None and (
            not isinstance(criteria, dict) or set(criteria) - {"false", "true"}
        ):
            raise ValueError("Noul criteria may contain only false and true descriptions")


def request_check(state, questions, config):
    if not isinstance(state, (str, dict, list)):
        raise ValueError("State must be text, an object, or a list")
    questions_check(questions, config)
    return bounded_json([state, questions], config.max_request_bytes)


def context_check(agent, state, questions):
    """Mirror upstream build_sequence budgets; refuse any silent truncation."""
    from laya.common import render_options, serialize_state

    tok = agent.tok

    def count(value):
        return len(tok(value.replace(tok.mask_token, " "), add_special_tokens=False)["input_ids"])

    state_tokens = count(serialize_state(state))
    max_len = agent.cfg.get("max_len", 512)
    head_max = agent.cfg.get("head_max_len", 192)
    totals = {}
    for qid, definition in questions.items():
        q = agent._to_internal(definition)
        lengths = [1 + count(" " + x) for x in render_options(q)]
        capped = [min(n, 49) for n in lengths]
        option_limit = 49
        budget = head_max - sum(capped)
        if budget < 16:
            option_limit = min(49, max(4, (head_max - 16) // len(lengths)))
            capped = [min(n, option_limit) for n in lengths]
            budget = head_max - sum(capped)
        instructions = count(f"{q['t']} question: {q['ins']}")
        if any(n > option_limit for n in lengths) or instructions > max(8, budget):
            raise ValueError(f"{qid}: instructions/criteria would be truncated; shorten them")
        total = 4 + instructions + sum(lengths) + state_tokens
        if total > max_len:
            raise ValueError(f"{qid}: needs {total} tokens, checkpoint limit {max_len}; split or summarize evidence")
        totals[qid] = total
    return totals
