#!/usr/bin/env python3
import json
import sys

if len(sys.argv) < 3:
    print("Usage: simulate_copilot_label_check.py <payload.json> <event_name>", file=sys.stderr)
    sys.exit(2)

payload_path = sys.argv[1]
event_name = sys.argv[2]

with open(payload_path, 'r', encoding='utf-8') as f:
    payload = json.load(f)

issue = payload.get('issue') or (payload.get('comment') and payload['comment'].get('issue'))

def labels_of(issue_obj):
    if not issue_obj:
        return []
    labels = issue_obj.get('labels') or []
    result = []
    for l in labels:
        if isinstance(l, str):
            result.append(l)
        elif isinstance(l, dict):
            name = l.get('name')
            if name:
                result.append(name)
    return result


def evaluate(issue_obj, event):
    if not issue_obj:
        return {"should_run": False, "reason": "no issue found in payload"}
    labels = labels_of(issue_obj)
    has_regression = 'regression' in labels
    # Current policy: trigger on regression label only
    should_run = has_regression
    return {
        "should_run": should_run,
        "labels": labels,
        "has_regression": has_regression,
        "event": event,
    }

result = evaluate(issue, event_name)
print(json.dumps(result, indent=2))
