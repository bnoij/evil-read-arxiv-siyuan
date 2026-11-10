import csv
import importlib.util
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


def load_search_module():
    script = ROOT / "start-my-day" / "scripts" / "rank_papers.py"
    spec = importlib.util.spec_from_file_location("search_arxiv_config_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


search = load_search_module()


class RecommendationConfigTests(unittest.TestCase):
    def test_domain_priority_changes_ranking_and_is_bounded(self):
        paper = {
            "title": "Robot Learning for Generalist Agents",
            "summary": "A foundation model for robot learning.",
            "categories": ["cs.RO"],
        }
        domains = {
            "low-priority": {
                "keywords": ["robot learning", "foundation model"],
                "arxiv_categories": ["cs.RO"],
                "priority": 1,
            },
            "high-priority": {
                "keywords": ["robot learning"],
                "arxiv_categories": ["cs.RO"],
                "priority": 10,
            },
        }

        score, domain, _ = search.calculate_relevance_score(paper, domains, [])

        self.assertEqual(domain, "high-priority")
        self.assertLessEqual(score, search.SCORE_MAX)

    def test_kimi_csv_normalization_dedupes_arxiv_versions(self):
        config = {
            "research_domains": {
                "agents": {"keywords": ["robot learning"], "arxiv_categories": ["cs.RO"], "priority": 5}
            },
            "excluded_keywords": [],
        }
        rows = [
            {
                "arxiv_id": "2601.00001v1",
                "title": "Robot Learning for Generalist Agents",
                "authors": '["Author One"]',
                "summary": "A foundation model for robot learning.",
                "published": "2026-01-02",
                "categories": '["cs.RO"]',
                "url": "https://arxiv.org/abs/2601.00001v1",
            },
            {
                "arxiv_id": "2601.00001v2",
                "title": "Robot Learning for Generalist Agents",
                "abstract": "A foundation model for robot learning.",
                "publicationDate": "2026-01-03",
                "citationCount": "12",
                "url": "https://arxiv.org/abs/2601.00001v2",
            },
        ]
        with TemporaryDirectory() as directory:
            source = Path(directory) / "kimi.csv"
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=sorted(set().union(*(row.keys() for row in rows))))
                writer.writeheader()
                writer.writerows(rows)

            result = search.rank_papers([source], config, datetime(2026, 1, 10), top_n=10)

        self.assertEqual(result["total_unique"], 1)
        self.assertEqual(result["top_papers"][0]["arxiv_id"], "2601.00001v2")
        self.assertEqual(result["top_papers"][0]["citationCount"], 12)

    def test_conference_ranking_filters_by_returned_venue(self):
        spec = importlib.util.spec_from_file_location(
            "conference_ranking", ROOT / "conf-papers/scripts/rank_conference_papers.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        papers = [
            {"title": "CVPR robot learning", "venue": "CVPR 2026", "summary": "robot learning", "categories": []},
            {"title": "Other robot learning", "venue": "OtherConf", "summary": "robot learning", "categories": []},
        ]
        config = {"research_domains": {"robots": {"keywords": ["robot learning"]}}, "excluded_keywords": []}

        result = module.rank_conference_papers(papers, config, ["CVPR"], top_n=10)

        self.assertEqual([paper["title"] for paper in result], ["CVPR robot learning"])

    def test_real_scholar_fields_map_year_venue_and_pdf_links(self):
        normalized = search.normalize_paper({
            "title": "Lerobot",
            "year": "2026",
            "citations": "126",
            "publication_info": "International Conference on Learning Representations",
            "pdf_links": "['https://arxiv.org/pdf/2601.00001']",
            "url": "https://example.com/paper",
        }, "scholar")

        self.assertEqual(normalized["published"], "2026")
        self.assertEqual(normalized["citationCount"], 126)
        self.assertEqual(normalized["venue"], "International Conference on Learning Representations")
        self.assertEqual(normalized["pdf_url"], "https://arxiv.org/pdf/2601.00001")
        self.assertEqual(normalized["arxiv_id"], "2601.00001")

    def test_missing_optional_kimi_fields_do_not_fail(self):
        normalized = search.normalize_paper({"title": "Empty metadata", "source": "scholar"}, "scholar")

        self.assertEqual(normalized["summary"], "")
        self.assertEqual(normalized["citationCount"], 0)
        self.assertEqual(normalized["authors"], [])


if __name__ == "__main__":
    unittest.main()
