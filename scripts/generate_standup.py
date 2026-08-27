#!/usr/bin/env python3
import os, json, re, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request, urllib.error

# ── Config ──────────────────────────────────────────────────────────
GITHUB_TOKEN    = os.environ["GITHUB_TOKEN"]
OPENROUTER_KEY  = os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
LLM_BASE_URL    = (os.environ.get("LLM_BASE_URL") or "https://api.deepseek.com").rstrip("/")
MODEL           = os.environ.get("LLM_MODEL") or os.environ.get("OPENROUTER_MODEL") or "deepseek-v4-flash"
GH_USERNAME     = os.environ.get("GH_USERNAME", "").strip()
TODAY           = datetime.now(timezone.utc).strftime("%Y-%m-%d")
SINCE           = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

# ── Helpers ──────────────────────────────────────────────────────────
def gh_get(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def llm_post(payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        LLM_BASE_URL + "/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# ── Resolve username ──────────────────────────────────────────────
if not GH_USERNAME:
    user = gh_get("https://api.github.com/user")
    GH_USERNAME = user["login"]
print(f"Username: {GH_USERNAME}, date: {TODAY}")

# ── Fetch GitHub events (last 24 h) ───────────────────────────────
WANTED = {"PushEvent", "PullRequestEvent", "IssuesEvent", "CreateEvent",
          "PullRequestReviewEvent", "IssueCommentEvent"}
events = []
try:
    raw = gh_get(f"https://api.github.com/users/{GH_USERNAME}/events?per_page=100")
    for e in raw:
        if e.get("created_at", "") < SINCE:
            continue
        if e["type"] not in WANTED:
            continue
        p = e.get("payload", {})
        repo = e.get("repo", {}).get("name", "unknown")
        if e["type"] == "PushEvent":
            commits = p.get("commits", [])
            msgs = [c["message"].splitlines()[0] for c in commits[:5]]
            events.append(f"Push to {repo}: {'; '.join(msgs)}")
        elif e["type"] == "PullRequestEvent":
            pr = p.get("pull_request", {})
            events.append(f"PR {p.get('action','')} [{repo}] #{pr.get('number','')} {pr.get('title','')}")
        elif e["type"] == "IssuesEvent":
            issue = p.get("issue", {})
            events.append(f"Issue {p.get('action','')} [{repo}] #{issue.get('number','')} {issue.get('title','')}")
        elif e["type"] == "CreateEvent":
            events.append(f"Created {p.get('ref_type','')} {p.get('ref','')} in {repo}")
        elif e["type"] == "PullRequestReviewEvent":
            pr = p.get("pull_request", {})
            events.append(f"Reviewed PR [{repo}] #{pr.get('number','')} {pr.get('title','')}")
        elif e["type"] == "IssueCommentEvent":
            issue = p.get("issue", {})
            events.append(f"Commented on [{repo}] #{issue.get('number','')} {issue.get('title','')}")
except Exception as ex:
    print(f"Warning: could not fetch events: {ex}")

if not events:
    events = ["（昨日无可记录的 GitHub 活动）"]

events_text = "\n".join(f"- {e}" for e in events)
print(f"Events collected: {len(events)}")

# ── Call Claude ───────────────────────────────────────────────────
prompt = (
    "你是一个研发助理。根据以下 GitHub 活动记录，生成一份简洁的每日站会汇报。\n"
    "格式：\n"
    "**【昨日完成】**\n- 条目\n\n"
    "**【今日计划】**\n- 基于昨日活动推断\n\n"
    "**【阻碍事项】**\n- 如有，否则写'无'\n\n"
    "要求：用第一人称，专业简洁，不超过150字。\n\n"
    f"活动记录：\n{events_text}"
)

try:
    resp = llm_post({
        "model": MODEL,
        "max_tokens": 512,
        "messages": [{"role": "user", "content": prompt}],
    })
    standup_body = resp["choices"][0]["message"]["content"].strip()
except Exception as ex:
    print(f"Warning: OpenRouter error: {ex}")
    standup_body = (
        "**【昨日完成】**\n"
        + events_text + "\n\n"
        "**【今日计划】**\n- 待定\n\n"
        "**【阻碍事项】**\n- 无"
    )

# 空响应也走兜底模板（避免写出空白站会）
if not standup_body.strip():
    standup_body = (
        "**【昨日完成】**\n" + events_text + "\n\n"
        "**【今日计划】**\n- 待定\n\n"
        "**【阻碍事项】**\n- 无"
    )

# ── Write standup file ────────────────────────────────────────────
standup_md = f"# 每日站会 - {TODAY}\n\n{standup_body}\n"
out_path = Path(f"standups/{TODAY}.md")
out_path.parent.mkdir(exist_ok=True)
out_path.write_text(standup_md, encoding="utf-8")
print(f"Written: {out_path}")

# ── Update index.json ─────────────────────────────────────────────
index_path = Path("standups/index.json")
if index_path.exists():
    index = json.loads(index_path.read_text())
else:
    index = []
if TODAY not in index:
    index.append(TODAY)
index.sort(reverse=True)
index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Updated: {index_path}  ({len(index)} entries)")