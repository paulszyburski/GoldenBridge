import json
import os
from collections import defaultdict
from datetime import datetime


def import_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def export_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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


def _is_scoreable(offer):
    return offer.get("scoring_status") == "scoreable_basic"


def _score_average_component(average_score):
    return min(40, (average_score / 100.0) * 40)


def _score_count_component(offers_count):
    if offers_count <= 0:
        return 0
    if offers_count == 1:
        return 5
    if offers_count == 2:
        return 10
    if offers_count == 3:
        return 15
    if offers_count == 4:
        return 20
    return 25


def _score_top_component(top_score):
    return min(20, (top_score / 100.0) * 20)


def _score_confidence_completeness(offers):
    if not offers:
        return 0

    confidence_weights = {"high": 1.0, "medium": 0.7, "low": 0.4}
    avg_conf_weight = sum(confidence_weights.get(o.get("score_confidence"), 0.4) for o in offers) / len(offers)

    completeness_hits = 0
    for offer in offers:
        has_breakdown = isinstance(offer.get("score_breakdown"), dict)
        has_signals = bool(offer.get("positive_signals"))
        has_source_ref = isinstance(offer.get("source_offer_ref"), dict)
        if has_breakdown and has_signals and has_source_ref:
            completeness_hits += 1

    completeness_ratio = completeness_hits / len(offers)
    return 10 * ((avg_conf_weight + completeness_ratio) / 2)


def _score_category_coherence(offers_count):
    if offers_count <= 1:
        return 1
    if offers_count == 2:
        return 3
    if offers_count <= 4:
        return 4
    return 5


def _cluster_strength(offers_count, cluster_score):
    if offers_count <= 1:
        return "weak"
    if offers_count == 2:
        return "possible"
    if offers_count <= 4:
        return "medium" if cluster_score >= 50 else "possible"
    return "strong" if cluster_score >= 60 else "medium"


def _top_offer_names(offers, n=3):
    ranked = sorted(offers, key=lambda o: o.get("preliminary_score", float("-inf")), reverse=True)
    return [offer.get("offer_name") for offer in ranked[:n] if offer.get("offer_name")]


def _cluster_status(offers_count, cluster_score, scoreable_count):
    if offers_count <= 1:
        return "weak"
    if offers_count == 2:
        return "possible"
    if offers_count >= 5 and cluster_score >= 60 and scoreable_count >= 2:
        return "strong"
    if offers_count >= 3 and cluster_score >= 50:
        return "medium"
    return "possible"


def _recommended_next_action(cluster_status, scoreable_count, medium_or_high_confidence_count):
    if cluster_status == "strong" and medium_or_high_confidence_count >= 2:
        return "PRIORITIZE_AND_SELECT_TOP_OFFERS"
    if scoreable_count == 0:
        return "ENRICH_OFFERS_IN_CATEGORY"
    if cluster_status in {"medium", "possible"}:
        return "REVIEW_TOP_OFFERS_AND_VALIDATE_SIGNALS"
    return "DEFER_CATEGORY"


def build_category_clusters(offers):
    grouped = defaultdict(list)
    for offer in offers:
        grouped[offer.get("category", "Unknown")].append(offer)

    clusters = []
    for category, category_offers in grouped.items():
        scoreable = [offer for offer in category_offers if _is_scoreable(offer)]
        ranked = sorted(category_offers, key=lambda o: o.get("preliminary_score", float("-inf")), reverse=True)

        offers_count = len(category_offers)
        scoreable_count = len(scoreable)
        top_score = ranked[0].get("preliminary_score", 0) if ranked else 0
        average_score = round(
            sum(offer.get("preliminary_score", 0) for offer in category_offers) / offers_count,
            2,
        ) if offers_count else 0

        medium_or_high_confidence_count = sum(
            1
            for offer in category_offers
            if offer.get("score_confidence") in {"medium", "high"}
        )

        avg_points = _score_average_component(average_score)
        count_points = _score_count_component(offers_count)
        top_points = _score_top_component(top_score)
        conf_points = _score_confidence_completeness(scoreable)
        coherence_points = _score_category_coherence(offers_count)

        cluster_score = round(avg_points + count_points + top_points + conf_points + coherence_points)
        cluster_status = _cluster_status(offers_count, cluster_score, scoreable_count)
        recommended_next_action = _recommended_next_action(
            cluster_status, scoreable_count, medium_or_high_confidence_count
        )

        clusters.append(
            {
                "category": category,
                "offers_count": offers_count,
                "average_score": average_score,
                "top_score": top_score,
                "scoreable_count": scoreable_count,
                "medium_or_high_confidence_count": medium_or_high_confidence_count,
                "top_offers": _top_offer_names(scoreable if scoreable else category_offers),
                "cluster_score": cluster_score,
                "cluster_status": cluster_status,
                "recommended_next_action": recommended_next_action,
            }
        )

    clusters.sort(key=lambda c: (c["cluster_score"], c["offers_count"], c["average_score"]), reverse=True)
    return clusters


def generate_category_cluster_scores(data, output_root="data/output"):
    today = datetime.now().strftime("%d-%m-%Y")
    now = datetime.now().strftime("%H-%M-%S")

    by_platform = defaultdict(list)
    for offer in data:
        by_platform[offer.get("platform_id", "unknown")].append(offer)

    written_paths = []
    for platform_id, offers in by_platform.items():
        clusters = build_category_clusters(offers)
        base_dir = f"{output_root}/category_cluster_scores/{platform_id}/{today}"
        output_path = _build_unique_output_path(base_dir, now)
        export_json(output_path, clusters)
        written_paths.append(output_path)

    return written_paths


if __name__ == "__main__":
    input_path = "data/scored/cj/advertisers/27-05-2026/12-43-39.json"
    offers = import_json(input_path)
    paths = generate_category_cluster_scores(offers)
    print("Generated category cluster scores:")
    for path in paths:
        print(path)
