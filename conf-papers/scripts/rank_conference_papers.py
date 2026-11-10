#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "start-my-day" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rank_papers import SCORE_MAX, _read_rows, calculate_quality_score, calculate_relevance_score, normalize_paper


def rank_conference_papers(papers, config, conferences, top_n=10):
    conference_names = [name.casefold() for name in conferences]
    candidates = []
    seen = set()
    for paper in papers:
        venue = str(paper.get("venue") or paper.get("publication") or paper.get("conference") or "")
        if not any(name in venue.casefold() for name in conference_names):
            continue
        normalized = normalize_paper({**paper, "venue": venue}, "scholar")
        identity = re.sub(r"v\d+$", "", normalized["arxiv_id"], flags=re.IGNORECASE) or re.sub(r"\W+", "", normalized["title"].casefold())
        if not identity or identity in seen:
            continue
        seen.add(identity)
        relevance, domain, keywords = calculate_relevance_score(
            normalized,
            config.get("research_domains", {}),
            config.get("excluded_keywords", []),
        )
        if relevance == 0:
            continue
        citations = normalized.get("influentialCitationCount", 0)
        popularity = min(citations / (100 / SCORE_MAX), SCORE_MAX)
        quality = calculate_quality_score(normalized.get("summary", ""))
        score = round((relevance / SCORE_MAX * 10) * 0.4 + (popularity / SCORE_MAX * 10) * 0.4 + (quality / SCORE_MAX * 10) * 0.2, 2)
        normalized["scores"] = {"relevance": round(relevance, 2), "popularity": round(popularity, 2), "quality": round(quality, 2), "recommendation": score}
        normalized["matched_domain"] = domain
        normalized["matched_keywords"] = keywords
        candidates.append(normalized)
    candidates.sort(key=lambda paper: paper["scores"]["recommendation"], reverse=True)
    return candidates[:top_n]


def main():
    parser = argparse.ArgumentParser(description="Filter and rank Scholar conference results")
    parser.add_argument("--input", nargs="+", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--conferences", required=True)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--output", default="-")
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
    if "research_domains" not in config:
        config["research_domains"] = {"conference": {"keywords": config.get("keywords", [])}}
    papers = []
    for source in args.input:
        papers.extend(_read_rows(Path(source)))
    result = rank_conference_papers(papers, config, args.conferences.split(","), args.top_n)
    rendered = json.dumps({"conferences": args.conferences.split(","), "coverage": "Scholar search results, not a complete DBLP listing", "top_papers": result}, ensure_ascii=False, indent=2, default=str)
    if args.output == "-":
        print(rendered)
    else:
        Path(args.output).write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
