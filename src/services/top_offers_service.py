import os
import json
from datetime import datetime
from collections import defaultdict

def import_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data

def export_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _allowed_candidates(data):
    return [
        candidate
        for candidate in data
        if candidate.get("scoring_status") not in {"blocked", "needs_enrichment"}
    ]


def pick_top_candidates(data, n=10):
    allowed_candidates = _allowed_candidates(data)

    ranked = sorted(
        allowed_candidates,
        key=lambda candidate: candidate.get("preliminary_score", float("-inf")),
        reverse=True,
    )

    return ranked[: max(0, n)]


def top_offers_by_category(data, n_per_category=10):
    allowed_candidates = _allowed_candidates(data)
    grouped = defaultdict(list)

    for candidate in allowed_candidates:
        grouped[candidate.get("category", "Unknown")].append(candidate)

    result = {}
    for category, offers in grouped.items():
        ranked = sorted(
            offers,
            key=lambda candidate: candidate.get("preliminary_score", float("-inf")),
            reverse=True,
        )
        result[category] = ranked[: max(0, n_per_category)]

    return result


def best_category_clusters(data):
    allowed_candidates = _allowed_candidates(data)
    grouped = defaultdict(list)

    for candidate in allowed_candidates:
        grouped[candidate.get("category", "Unknown")].append(candidate)

    clusters = []
    for category, offers in grouped.items():
        total_offers = len(offers)
        total_score = sum(offer.get("preliminary_score", 0) for offer in offers)
        average_score = round(total_score / total_offers, 2) if total_offers else 0

        clusters.append(
            {
                "category": category,
                "offers_count": total_offers,
                "average_score": average_score,
                "top_offer": max(
                    offers,
                    key=lambda offer: offer.get("preliminary_score", float("-inf")),
                ),
            }
        )

    clusters.sort(
        key=lambda cluster: (cluster["average_score"], cluster["offers_count"]),
        reverse=True,
    )
    return clusters


def _group_by_platform(data):
    grouped = defaultdict(list)
    for candidate in data:
        grouped[candidate.get("platform_id")].append(candidate)
    return grouped


def _build_unique_output_path(base_dir, timestamp):
    path = f"{base_dir}/{timestamp}.json"
    if not os.path.exists(path):
        return path

    counter = 1
    while True:
        candidate = f"{base_dir}/{timestamp}-{counter:02d}.json"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def generate_rankings(data, n=10, output_root="data/output"):
    today = datetime.now().strftime("%d-%m-%Y")
    now = datetime.now().strftime("%H-%M-%S")
    grouped_platforms = _group_by_platform(data)

    for platform_id, platform_data in grouped_platforms.items():
        overall = pick_top_candidates(platform_data, n=n)
        by_category = top_offers_by_category(platform_data, n_per_category=n)
        category_clusters = best_category_clusters(platform_data)

        overall_dir = f"{output_root}/top_offers_overall/{platform_id}/{today}"
        by_category_dir = f"{output_root}/top_offers_by_category/{platform_id}/{today}"
        clusters_dir = f"{output_root}/best_category_clusters/{platform_id}/{today}"

        overall_path = _build_unique_output_path(overall_dir, now)
        by_category_path = _build_unique_output_path(by_category_dir, now)
        clusters_path = _build_unique_output_path(clusters_dir, now)

        export_json(overall_path, overall)
        export_json(by_category_path, by_category)
        export_json(clusters_path, category_clusters)

if __name__ == "__main__":
    input_path = "data/scored/cj/advertisers/27-05-2026/12-43-39.json"

    data = import_json(input_path)
    generate_rankings(data, n=10, output_root="data/output")
    print("Generated: top_offers_overall, top_offers_by_category, best_category_clusters")
