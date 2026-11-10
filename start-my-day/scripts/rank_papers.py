#!/usr/bin/env python3
import argparse
import csv
import json
import logging
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

SCORE_MAX = 3.0
RELEVANCE_TITLE_KEYWORD_BOOST = 0.5
RELEVANCE_SUMMARY_KEYWORD_BOOST = 0.3
RELEVANCE_CATEGORY_MATCH_BOOST = 1.0
RECENCY_THRESHOLDS = [(30, 3.0), (90, 2.0), (180, 1.0)]
RECENCY_DEFAULT = 0.0
POPULARITY_INFLUENTIAL_CITATION_FULL_SCORE = 100
WEIGHTS_NORMAL = {"relevance": 0.40, "recency": 0.20, "popularity": 0.30, "quality": 0.10}
WEIGHTS_HOT = {"relevance": 0.35, "recency": 0.10, "popularity": 0.45, "quality": 0.10}


def load_research_config(config_path: str) -> Dict:
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _first(row: Dict, *names: str, default=""):
    for name in names:
        value = row.get(name)
        if value is not None and value != "":
            return value
    return default


def _integer(value) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _list(value) -> List:
    if isinstance(value, list):
        return value
    if not value:
        return []
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        return [part.strip() for part in re.split(r"[;,]", text) if part.strip()]
    return [value]


def _datetime(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def normalize_paper(row: Dict, source: str = "arxiv") -> Dict:
    source = str(row.get("source") or source or "arxiv").lower()
    url = str(_first(row, "url", "entry_id", "link", default=""))
    arxiv_id = str(_first(row, "arxiv_id", "arxivId", "id", default="")).strip()
    if "arxiv.org" in arxiv_id:
        match = re.search(r"arxiv\.org/(?:abs|pdf)/([^\s/]+)", arxiv_id)
        arxiv_id = match.group(1) if match else ""
    pdf_links = str(row.get("pdf_links") or "")
    if not arxiv_id:
        match = re.search(r"arxiv\.org/(?:abs|pdf)/([^\s/'\"\]]+)", f"{url} {pdf_links}")
        arxiv_id = match.group(1) if match else ""
    arxiv_id = re.sub(r"\.pdf$", "", arxiv_id, flags=re.IGNORECASE)
    published = str(_first(row, "published", "publicationDate", "date", "year", default=""))
    summary = str(_first(row, "summary", "abstract", "abstractNote", default=""))
    pdf_url = str(_first(row, "pdf_url", "pdfUrl", "pdf", default=""))
    if not pdf_url and pdf_links:
        match = re.search(r"https?://[^\s'\"\]]+", pdf_links)
        pdf_url = match.group(0) if match else ""
    authors = _list(_first(row, "authors", "author", "creators", default=[]))
    authors = [str(author.get("name", "")) if isinstance(author, dict) else str(author) for author in authors]
    return {
        "arxiv_id": arxiv_id,
        "title": str(_first(row, "title", "name", default="")).strip(),
        "authors": [author for author in authors if author],
        "summary": summary,
        "abstract": summary,
        "published": published,
        "published_date": _datetime(published),
        "categories": _list(_first(row, "categories", "category", default=[])),
        "url": url or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""),
        "pdf_url": pdf_url or (f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else ""),
        "doi": str(_first(row, "doi", "DOI", default="")),
        "venue": str(_first(row, "venue", "publication", "publication_info", "journal", "conference", default="")),
        "citationCount": _integer(_first(row, "citationCount", "citations", default=0)),
        "influentialCitationCount": _integer(_first(row, "influentialCitationCount", "influentialCitations", "citationCount", "citations", default=0)),
        "source": source,
    }


def calculate_relevance_score(paper: Dict, domains: Dict, excluded_keywords: List[str], focus_keywords: List[str] = None) -> Tuple[float, Optional[str], List[str]]:
    focus_keywords = focus_keywords or []
    title = paper.get("title", "").lower()
    summary = paper.get("summary", "").lower() if "summary" in paper else paper.get("abstract", "").lower()
    categories = set(paper.get("categories", []))
    for keyword in excluded_keywords:
        if keyword.lower() in title or keyword.lower() in summary:
            return 0, None, []
    focus_score = 0.0
    focus_matched = []
    for keyword in focus_keywords:
        keyword_lower = keyword.lower().strip()
        if not keyword_lower:
            continue
        if keyword_lower in title:
            focus_score += 2.0
            focus_matched.append(keyword)
        elif keyword_lower in summary:
            focus_score += 1.0
            focus_matched.append(keyword)
    max_domain_score = 0
    best_domain = None
    domain_matched_keywords = []
    for domain_name, domain_config in domains.items():
        score = 0
        matched = []
        for keyword in domain_config.get("keywords", []):
            keyword_lower = keyword.lower()
            if keyword_lower in title:
                score += RELEVANCE_TITLE_KEYWORD_BOOST
                matched.append(keyword)
            elif keyword_lower in summary:
                score += RELEVANCE_SUMMARY_KEYWORD_BOOST
                matched.append(keyword)
        for category in domain_config.get("arxiv_categories", []):
            if category in categories:
                score += RELEVANCE_CATEGORY_MATCH_BOOST
                matched.append(category)
        try:
            priority = max(1.0, min(10.0, float(domain_config.get("priority", 5))))
        except (TypeError, ValueError):
            priority = 5.0
        weighted_score = min(score * (priority / 5.0), SCORE_MAX)
        if weighted_score > max_domain_score:
            max_domain_score = weighted_score
            best_domain = domain_name
            domain_matched_keywords = matched
    if focus_keywords:
        return focus_score + max_domain_score * 0.3, best_domain or ("搜索结果" if focus_matched else None), focus_matched + [k for k in domain_matched_keywords if k not in focus_matched]
    return max_domain_score, best_domain, domain_matched_keywords


def calculate_recency_score(published_date: Optional[datetime], reference_date: Optional[datetime] = None) -> float:
    if published_date is None:
        return 0.0
    reference_date = reference_date or datetime.now(published_date.tzinfo)
    if reference_date.tzinfo != published_date.tzinfo:
        reference_date = reference_date.replace(tzinfo=published_date.tzinfo)
    days_diff = (reference_date - published_date).days
    for max_days, score in RECENCY_THRESHOLDS:
        if days_diff <= max_days:
            return score
    return RECENCY_DEFAULT


def calculate_quality_score(summary: str) -> float:
    if not summary:
        return 0.0
    score = 0.0
    summary_lower = summary.lower()
    strong = ["state-of-the-art", "sota", "breakthrough", "first", "surpass", "outperform", "pioneering"]
    weak = ["novel", "propose", "introduce", "new approach", "new method", "innovative"]
    methods = ["framework", "architecture", "algorithm", "mechanism", "pipeline", "end-to-end"]
    quantitative = ["outperforms", "improves by", "achieves", "accuracy", "f1", "bleu", "rouge", "beats", "surpasses"]
    experiments = ["experiment", "evaluation", "benchmark", "ablation", "baseline", "comparison"]
    strong_count = sum(indicator in summary_lower for indicator in strong)
    if strong_count >= 2:
        score += 1.0
    elif strong_count == 1:
        score += 0.7
    elif any(indicator in summary_lower for indicator in weak):
        score += 0.3
    if any(indicator in summary_lower for indicator in methods):
        score += 0.5
    if any(indicator in summary_lower for indicator in quantitative):
        score += 0.8
    elif any(indicator in summary_lower for indicator in experiments):
        score += 0.4
    return min(score, SCORE_MAX)


def calculate_recommendation_score(relevance_score: float, recency_score: float, popularity_score: float, quality_score: float, is_hot_paper: bool = False) -> float:
    scores = {"relevance": relevance_score, "recency": recency_score, "popularity": popularity_score, "quality": quality_score}
    normalized = {key: (value / SCORE_MAX) * 10 for key, value in scores.items()}
    weights = WEIGHTS_HOT if is_hot_paper else WEIGHTS_NORMAL
    return round(sum(normalized[key] * weights[key] for key in weights), 2)


def filter_and_score_papers(papers: List[Dict], config: Dict, target_date: Optional[datetime] = None, is_hot_paper_batch: bool = False, focus_keywords: List[str] = None) -> List[Dict]:
    domains = config.get("research_domains", {})
    excluded_keywords = config.get("excluded_keywords", [])
    scored_papers = []
    for paper in papers:
        relevance, matched_domain, matched_keywords = calculate_relevance_score(paper, domains, excluded_keywords, focus_keywords=focus_keywords or [])
        if relevance == 0:
            continue
        recency = calculate_recency_score(paper.get("published_date"), target_date)
        if is_hot_paper_batch:
            popularity = min(paper.get("influentialCitationCount", 0) / (POPULARITY_INFLUENTIAL_CITATION_FULL_SCORE / SCORE_MAX), SCORE_MAX)
        else:
            days_old = (target_date - paper["published_date"]).days if target_date and paper.get("published_date") else 365
            popularity = 2.0 if days_old <= 7 else 1.5 if days_old <= 14 else 1.0 if days_old <= 30 else 0.5
        quality = calculate_quality_score(paper.get("summary", ""))
        recommendation = calculate_recommendation_score(relevance, recency, popularity, quality, is_hot_paper_batch)
        paper["scores"] = {"relevance": round(relevance, 2), "recency": round(recency, 2), "popularity": round(popularity, 2), "quality": round(quality, 2), "recommendation": recommendation}
        paper["matched_domain"] = matched_domain
        paper["matched_keywords"] = matched_keywords
        paper["is_hot_paper"] = is_hot_paper_batch
        scored_papers.append(paper)
    scored_papers.sort(key=lambda paper: paper["scores"]["recommendation"], reverse=True)
    return scored_papers


def _read_rows(path: Path) -> List[Dict]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data.get("top_papers") or data.get("papers") or data.get("data") or []
        return data
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def paper_aliases(paper: Dict) -> List[str]:
    arxiv_id = re.sub(r"v\d+$", "", paper.get("arxiv_id", ""), flags=re.IGNORECASE).lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", paper.get("doi", ""), flags=re.IGNORECASE).lower()
    title = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", paper.get("title", "").lower())
    return [value for value in (f"arxiv:{arxiv_id}" if arxiv_id else "", f"doi:{doi}" if doi else "", f"title:{title}" if title else "") if value]


def merge_paper_group(group: Dict, paper: Dict, is_hot: bool) -> None:
    current = group["paper"]
    current_match = re.search(r"v(\d+)$", current.get("arxiv_id", ""), re.IGNORECASE)
    paper_match = re.search(r"v(\d+)$", paper.get("arxiv_id", ""), re.IGNORECASE)
    current_version = int(current_match.group(1)) if current_match else 0
    paper_version = int(paper_match.group(1)) if paper_match else 0
    preferred, other = (paper, current) if paper_version >= current_version else (current, paper)
    for field, value in other.items():
        if not preferred.get(field) and value:
            preferred[field] = value
    preferred["citationCount"] = max(current.get("citationCount", 0), paper.get("citationCount", 0))
    preferred["influentialCitationCount"] = max(current.get("influentialCitationCount", 0), paper.get("influentialCitationCount", 0))
    group["paper"] = preferred
    group["hot"] = group["hot"] or is_hot


def rank_papers(inputs: List[Path], config: Dict, target_date: datetime, top_n: int) -> Dict:
    total = 0
    groups = {}
    aliases = {}
    for input_path in inputs:
        path = Path(input_path)
        rows = _read_rows(path)
        total += len(rows)
        for row in rows:
            source = str(row.get("source") or ("scholar" if "scholar" in path.name.lower() else "arxiv")).lower()
            paper = normalize_paper(row, source)
            keys = paper_aliases(paper)
            if not keys:
                continue
            is_hot = source == "scholar"
            existing = list(dict.fromkeys(aliases[key] for key in keys if key in aliases))
            if not existing:
                key = keys[0]
                groups[key] = {"paper": paper, "hot": is_hot}
            else:
                key = existing[0]
                merge_paper_group(groups[key], paper, is_hot)
                for duplicate in existing[1:]:
                    other = groups.pop(duplicate)
                    merge_paper_group(groups[key], other["paper"], other["hot"])
                    for alias, mapped in list(aliases.items()):
                        if mapped == duplicate:
                            aliases[alias] = key
            for alias_value in keys:
                aliases[alias_value] = key
    scored = []
    for group in groups.values():
        scored.extend(filter_and_score_papers([group["paper"]], config, target_date, is_hot_paper_batch=group["hot"]))
    scored.sort(key=lambda paper: paper["scores"]["recommendation"], reverse=True)
    return {"target_date": target_date.strftime("%Y-%m-%d"), "total_found": total, "total_unique": len(groups), "top_papers": scored[:top_n]}


def main():
    parser = argparse.ArgumentParser(description="Rank Kimi arXiv/Scholar CSV or JSON results locally")
    parser.add_argument("--input", nargs="+", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", default="-")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--target-date", default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    target_date = datetime.strptime(args.target_date, "%Y-%m-%d") if args.target_date else datetime.now()
    result = rank_papers([Path(value) for value in args.input], load_research_config(args.config), target_date, args.top_n)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    if args.output == "-":
        print(rendered)
    else:
        Path(args.output).write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
