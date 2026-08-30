"""
Extracts file "churn" from git history — how often a file changes
and how many different people touch it. High churn + high
complexity together are the strongest predictor of expensive bugs.

We only ever read git metadata (commit messages, file paths, author
names/dates) — never diff content — and nothing here writes any of
that to disk outside the ephemeral clone.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from git import Repo


def compute_churn_metrics(repo_path: str, days: int = 90) -> dict[str, dict]:
    """
    Returns { file_path: {"churn": int, "unique_authors": int, "last_modified": datetime} }
    for every file touched in the last `days` days on the current branch.
    """
    repo = Repo(repo_path)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    churn_count: dict[str, int] = defaultdict(int)
    authors_by_file: dict[str, set[str]] = defaultdict(set)
    last_modified: dict[str, datetime] = {}

    for commit in repo.iter_commits(since=since.isoformat()):
        commit_dt = commit.committed_datetime
        for file_path in commit.stats.files.keys():
            churn_count[file_path] += 1
            authors_by_file[file_path].add(commit.author.email or commit.author.name)
            if file_path not in last_modified or commit_dt > last_modified[file_path]:
                last_modified[file_path] = commit_dt

    return {
        file_path: {
            "churn": churn_count[file_path],
            "unique_authors": len(authors_by_file[file_path]),
            "last_modified": last_modified[file_path],
        }
        for file_path in churn_count
    }
