#!/usr/bin/env python3
"""
Generate assets/activity.svg for GitHub profile README.

Fetches real contribution data via GitHub GraphQL API and renders a
pure SVG (no <image> elements — Camo proxy strips them in README).

Environment variables:
  GITHUB_TOKEN     Required. PAT with public_repo scope.
  GITHUB_USERNAME  Optional. Default: soumadipcodeEnthusiast
"""

import math
import os
import shutil
import sys
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "soumadipcodeEnthusiast")
GRAPHQL_URL = "https://api.github.com/graphql"

_here = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(_here, "..", "assets", "activity.svg")
BACKUP_PATH = OUTPUT_PATH + ".bak"

# Verified orgs in display order (from author: search, this session).
# The script augments this list with anything the API returns.
KNOWN_ORGS = ["kubeflow", "volcano-sh", "kubevirt", "argoproj", "OneBusAway"]

# Verified repos in display order.
VERIFIED_REPOS = [
    "kubeflow/notebooks",
    "volcano-sh/kthena",
    "kubevirt/kubevirt",
    "argoproj/argo-cd",
    "OneBusAway/watchdog",
]

# ---------------------------------------------------------------------------
# GraphQL fetch
# ---------------------------------------------------------------------------

QUERY = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      commitContributionsByRepository(maxRepositories: 25) {
        contributions { totalCount }
        repository { nameWithOwner owner { login } }
      }
      pullRequestContributions(first: 100) {
        nodes {
          pullRequest {
            repository { nameWithOwner owner { login } }
          }
        }
      }
      issueContributions(first: 100) {
        nodes {
          issue {
            repository { nameWithOwner owner { login } }
          }
        }
      }
      pullRequestReviewContributions(first: 100) {
        nodes {
          pullRequest {
            repository { nameWithOwner owner { login } }
          }
        }
      }
    }
  }
}
"""


def _gql(query, variables):
    headers = {
        "Authorization": f"bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if "errors" in body:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body["data"]


def fetch_data():
    data = _gql(QUERY, {"username": GITHUB_USERNAME})
    cc = data["user"]["contributionsCollection"]

    commits = cc["totalCommitContributions"]
    prs = cc["totalPullRequestContributions"]
    issues = cc["totalIssueContributions"]
    reviews = cc["totalPullRequestReviewContributions"]

    # Collect orgs from all contribution types
    contributed_orgs: set[str] = set()
    for entry in cc["commitContributionsByRepository"]:
        contributed_orgs.add(entry["repository"]["owner"]["login"])
    for node in cc["pullRequestContributions"]["nodes"]:
        contributed_orgs.add(node["pullRequest"]["repository"]["owner"]["login"])
    for node in cc["issueContributions"]["nodes"]:
        contributed_orgs.add(node["issue"]["repository"]["owner"]["login"])
    for node in cc["pullRequestReviewContributions"]["nodes"]:
        contributed_orgs.add(node["pullRequest"]["repository"]["owner"]["login"])
    contributed_orgs.discard(GITHUB_USERNAME)  # own repos are not orgs

    # Order: known verified orgs first, then any extras from API
    orgs_ordered = [o for o in KNOWN_ORGS if o in contributed_orgs]
    for o in sorted(contributed_orgs):
        if o not in orgs_ordered:
            orgs_ordered.append(o)

    # Only show verified repos whose org appears in the contribution data
    contributed_org_set = {o.lower() for o in contributed_orgs}
    repos = [
        r for r in VERIFIED_REPOS
        if r.split("/")[0].lower() in contributed_org_set
    ]

    return {
        "commits": commits,
        "prs": prs,
        "issues": issues,
        "reviews": reviews,
        "orgs": orgs_ordered,
        "repos": repos,
    }


# ---------------------------------------------------------------------------
# Percentages
# ---------------------------------------------------------------------------

def calculate_percentages(data):
    """
    Denominator = commits + PRs + issues + reviews (all contribution events
    GitHub's contributionsCollection reports for the current contribution year).
    Each percentage = category_count / total * 100, rounded to nearest integer.
    """
    total = data["commits"] + data["prs"] + data["issues"] + data["reviews"]
    if total == 0:
        return {k: 0 for k in ("commits", "prs", "issues", "reviews")}, 0
    pcts = {
        "commits": round(data["commits"] / total * 100),
        "prs": round(data["prs"] / total * 100),
        "issues": round(data["issues"] / total * 100),
        "reviews": round(data["reviews"] / total * 100),
    }
    return pcts, total


# ---------------------------------------------------------------------------
# SVG generation helpers
# ---------------------------------------------------------------------------

def _xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _radar_vertex(pct, cx, cy, radius, angle_deg):
    r = radius * max(pct, 2) / 100  # min 2px so zero shows a dot
    rad = math.radians(angle_deg)
    return (cx + r * math.cos(rad), cy + r * math.sin(rad))


def _pts(points):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


# ---------------------------------------------------------------------------
# SVG render
# ---------------------------------------------------------------------------

MONO = "'SFMono-Regular',Consolas,'Liberation Mono',monospace"
W, H = 900, 330


def generate_svg(data, pcts, total_contribs, updated_at):
    orgs = data["orgs"]
    repos = data["repos"]

    lines = []
    a = lines.append

    a(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">')
    a('  <rect width="100%" height="100%" fill="#0D1117"/>')

    # subtle dot texture
    a('  <defs>')
    a('    <pattern id="dp" x="0" y="0" width="14" height="14" patternUnits="userSpaceOnUse">')
    a('      <circle cx="1" cy="1" r="0.55" fill="#1C2128" opacity="0.8"/>')
    a('    </pattern>')
    a('  </defs>')
    a('  <rect width="100%" height="100%" fill="url(#dp)"/>')

    pad = 24

    # -----------------------------------------------------------------------
    # ORG BADGES (top row, text-only — no <image>, Camo-safe)
    # -----------------------------------------------------------------------
    badge_h = 26
    bx = pad
    by = pad
    max_show = 5
    shown_orgs = orgs[:max_show]
    remaining = max(0, len(orgs) - max_show)

    for org in shown_orgs:
        label = f"@{org}"
        # Approx monospace char width ~7px at 11px font
        bw = len(label) * 7 + 24
        bw = max(bw, 80)

        a(f'  <rect x="{bx}" y="{by}" width="{bw}" height="{badge_h}" rx="13"'
          f' fill="#161B22" stroke="#30363D" stroke-width="1"/>')
        a(f'  <circle cx="{bx + 14}" cy="{by + 13}" r="4" fill="#238636"/>')
        a(f'  <text x="{bx + 24}" y="{by + 17}"'
          f' font-family={MONO!r} font-size="11" fill="#E6EDF3">{_xml(label)}</text>')
        bx += bw + 8

    if remaining > 0:
        more = f"+{remaining} more"
        mw = len(more) * 7 + 20
        a(f'  <rect x="{bx}" y="{by}" width="{mw}" height="{badge_h}" rx="13"'
          f' fill="#0D1117" stroke="#30363D" stroke-width="1" stroke-dasharray="4,2"/>')
        a(f'  <text x="{bx + mw // 2}" y="{by + 17}" text-anchor="middle"'
          f' font-family={MONO!r} font-size="11" fill="#484F58">{_xml(more)}</text>')

    # -----------------------------------------------------------------------
    # Divider
    # -----------------------------------------------------------------------
    div_y = by + badge_h + 14
    a(f'  <line x1="{pad}" y1="{div_y}" x2="{W - pad}" y2="{div_y}"'
      f' stroke="#21262D" stroke-width="1"/>')

    # -----------------------------------------------------------------------
    # TWO COLUMNS
    # -----------------------------------------------------------------------
    col_y = div_y + 16
    left_w = 410
    right_x = pad + left_w + 20
    right_w = W - right_x - pad
    radar_cx = right_x + right_w // 2
    radar_r = 82
    # Center radar vertically in the right column
    radar_cy = col_y + 20 + radar_r + 16

    # Vertical divider
    vdiv_x = pad + left_w + 10
    a(f'  <line x1="{vdiv_x}" y1="{col_y}" x2="{vdiv_x}" y2="{H - 22}"'
      f' stroke="#21262D" stroke-width="1"/>')

    # --- LEFT: Activity overview ---
    a(f'  <text x="{pad}" y="{col_y + 13}"'
      f' font-family={MONO!r} font-size="13" font-weight="700" fill="#E6EDF3">Activity overview</text>')
    a(f'  <text x="{pad}" y="{col_y + 33}"'
      f' font-family={MONO!r} font-size="11" fill="#8B949E">Contributed to</text>')

    ry = col_y + 55
    for repo in repos:
        a(f'  <circle cx="{pad + 6}" cy="{ry - 4}" r="3.5" fill="#238636"/>')
        a(f'  <text x="{pad + 18}" y="{ry}"'
          f' font-family={MONO!r} font-size="11" fill="#58A6FF">{_xml(repo)}</text>')
        ry += 24

    # Footer line
    note = (
        f"Updated {updated_at} UTC  ·  "
        f"denominator: {total_contribs} total events (commits+PRs+issues+reviews, current contribution year)"
    )
    a(f'  <text x="{pad}" y="{H - 8}"'
      f' font-family={MONO!r} font-size="9" fill="#484F58">{_xml(note)}</text>')

    # --- RIGHT: Radar chart ---
    a(f'  <text x="{radar_cx}" y="{col_y + 13}" text-anchor="middle"'
      f' font-family={MONO!r} font-size="11" fill="#8B949E">Contribution types</text>')

    # Background rings at 25 / 50 / 75 / 100 %
    for ring in [25, 50, 75, 100]:
        rr = radar_r * ring / 100
        a(f'  <circle cx="{radar_cx}" cy="{radar_cy}" r="{rr:.1f}"'
          f' fill="none" stroke="#21262D" stroke-width="0.8"/>')

    # Axes: top=Commits (270°), right=PRs (0°), bottom=Issues (90°), left=Reviews (180°)
    axis_cfg = [
        (270, "Commits",      pcts["commits"]),
        (0,   "Pull Requests", pcts["prs"]),
        (90,  "Issues",       pcts["issues"]),
        (180, "Reviews",      pcts["reviews"]),
    ]
    for deg, _name, _pct in axis_cfg:
        rad = math.radians(deg)
        x2 = radar_cx + radar_r * math.cos(rad)
        y2 = radar_cy + radar_r * math.sin(rad)
        a(f'  <line x1="{radar_cx}" y1="{radar_cy}" x2="{x2:.1f}" y2="{y2:.1f}"'
          f' stroke="#21262D" stroke-width="0.8"/>')

    # Data polygon
    verts = [_radar_vertex(pct, radar_cx, radar_cy, radar_r, deg)
             for deg, _, pct in axis_cfg]
    a(f'  <polygon points="{_pts(verts)}"'
      f' fill="#238636" fill-opacity="0.22" stroke="#2EA043" stroke-width="1.5"/>')

    # Data point dots
    for vx, vy in verts:
        a(f'  <circle cx="{vx:.1f}" cy="{vy:.1f}" r="4"'
          f' fill="#2EA043" stroke="#0D1117" stroke-width="1.5"/>')

    # Axis labels + percentages
    label_offsets = {270: (0, -18), 0: (18, 0), 90: (0, 20), 180: (-18, 0)}
    anchors = {270: "middle", 0: "start", 90: "middle", 180: "end"}
    for deg, name, pct in axis_cfg:
        rad = math.radians(deg)
        dx, dy = label_offsets[deg]
        lx = radar_cx + (radar_r + 18) * math.cos(rad) + dx
        ly = radar_cy + (radar_r + 18) * math.sin(rad) + dy
        anchor = anchors[deg]
        a(f'  <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}"'
          f' font-family={MONO!r} font-size="10" fill="#8B949E">{_xml(name)}</text>')
        a(f'  <text x="{lx:.1f}" y="{ly + 13:.1f}" text-anchor="{anchor}"'
          f' font-family={MONO!r} font-size="11" font-weight="700" fill="#2EA043">{pct}%</text>')

    a('</svg>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # Preserve last good SVG before attempting update
    if os.path.exists(OUTPUT_PATH):
        shutil.copy2(OUTPUT_PATH, BACKUP_PATH)

    try:
        print(f"Fetching contribution data for @{GITHUB_USERNAME}…")
        data = fetch_data()
        pcts, total = calculate_percentages(data)

        print(
            f"  Commits: {data['commits']}  PRs: {data['prs']}  "
            f"Issues: {data['issues']}  Reviews: {data['reviews']}  Total: {total}"
        )
        print(
            f"  Percentages — Commits: {pcts['commits']}%  PRs: {pcts['prs']}%  "
            f"Issues: {pcts['issues']}%  Reviews: {pcts['reviews']}%"
        )
        print(f"  Orgs: {data['orgs']}")
        print(f"  Repos: {data['repos']}")

        updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        svg = generate_svg(data, pcts, total, updated_at)

        os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"Written: {OUTPUT_PATH}")

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if os.path.exists(BACKUP_PATH):
            shutil.copy2(BACKUP_PATH, OUTPUT_PATH)
            print("Restored previous SVG from backup.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
