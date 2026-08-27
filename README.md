# standup-bot

Reads your GitHub activity from the past 24 hours and generates a daily standup report using Claude. Results are committed to this repo and viewable via GitHub Pages.

## Setup

### 1. Configure Secrets

In your repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `LLM_API_KEY` | Your DeepSeek key from [platform.deepseek.com](https://platform.deepseek.com) (`OPENROUTER_API_KEY` also accepted) |
| `GH_USERNAME` | Your GitHub username (e.g. `lvwei`) |

`GITHUB_TOKEN` is provided automatically by Actions.

### 2. Enable GitHub Pages

**Settings → Pages → Source → GitHub Actions**

The `index.html` at the repo root becomes your standup archive viewer.

### 3. Grant write permission to Actions

**Settings → Actions → General → Workflow permissions → Read and write permissions**

This allows the workflow to commit the generated standup file.

### 4. Run manually (first test)

**Actions → Daily Standup → Run workflow**

Check the run logs to confirm events are fetched and Claude responds correctly.

## How it works

Every weekday at 08:30 UTC (16:30 CST) the workflow:

1. Fetches your GitHub events from the past 24 hours (push, PRs, issues, reviews)
2. Sends them to Claude with a prompt to generate a standup in 【昨日完成】【今日计划】【阻碍事项】 format
3. Writes `standups/YYYY-MM-DD.md`
4. Updates `standups/index.json`
5. Commits and pushes both files

## Project structure

```
standup-bot/
├── .github/workflows/daily-standup.yml   # Scheduled job
├── standups/
│   ├── index.json                         # List of all standup dates
│   └── 2026-08-19.md                      # Sample standup
├── index.html                             # Archive viewer (GitHub Pages)
├── .nojekyll                              # Disable Jekyll
└── README.md
```

## Customizing the Claude prompt

Edit the `prompt` variable in the workflow's Python script to change the standup format, language, or length. The model is read from the `LLM_MODEL` repository variable (default `deepseek-v4-flash`) — no code change needed to switch.
