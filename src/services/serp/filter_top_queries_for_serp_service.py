import os
import json
from datetime import datetime

def import_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def export_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def filter_query_candidate(query_candidate):
    query_candidate["serp_selection_status"] = "validated"
    query_candidate["serp_selection_reason"] = []
    if query_candidate["status"] != "validated":
        query_candidate["serp_selection_status"] = "rejected"
        query_candidate["serp_selection_reason"].append(f"Status set to {query_candidate['status']}")
    if query_candidate["target_market"] != "EN-US":
        query_candidate["serp_selection_status"] = "rejected"
        query_candidate["serp_selection_reason"].append(f"Target market set to {query_candidate['target_market']}")
    if query_candidate["language"] != "en":
        query_candidate["serp_selection_status"] = "rejected"
        query_candidate["serp_selection_reason"].append(f"Language set to {query_candidate['language']}")
    if query_candidate["buyer_intent_score"] < 0.50:
        query_candidate["serp_selection_status"] = "rejected"
        query_candidate["serp_selection_reason"].append(
            f"Buyer intent score too low: {query_candidate['buyer_intent_score']}"
        )
    return query_candidate

def filter_queries(data):
    serp_selected_offers = []
    serp_skipped_offers = []
    for offer in data:
        selected_queries = []
        skipped_queries = []
        for query_candidate in offer["queriesCandidates"]:
            filtered_query = filter_query_candidate(query_candidate)
            if filtered_query["serp_selection_status"] == "rejected":
                skipped_queries.append(filtered_query)
            else:
                selected_queries.append(filtered_query)

        if selected_queries:
            serp_selected_offers.append({
                "platform_id": offer["platform_id"],
                "offer_id": offer["offer_id"],
                "name": offer["name"],
                "queriesCandidates": selected_queries
            })

        if skipped_queries:
            serp_skipped_offers.append({
                "platform_id": offer["platform_id"],
                "offer_id": offer["offer_id"],
                "name": offer["name"],
                "queriesCandidates": skipped_queries
            })
    return serp_selected_offers, serp_skipped_offers


if __name__ == "__main__":
    now = datetime.now().strftime("%H-%M-%S")
    today = datetime.now().strftime("%d-%m-%Y")
    input_path = "data/query_candidates/buyer_intent_scored/cj/advertisers/07-06-2026/15-35-58.json"
    selected_output_path = f"data/query_candidates/serp/filter/serp_selected/cj/advertisers/{today}/{now}.json"
    skipped_output_path = f"data/query_candidates/serp/filter/serp_skipped/cj/advertisers/{today}/{now}.json"

    offers = import_json(input_path)
    print(f"Filtering SERP candidates for {len(offers)} offers...")
    serp_selected_offers, serp_skipped_offers = filter_queries(offers)
    export_json(serp_selected_offers, selected_output_path)
    export_json(serp_skipped_offers, skipped_output_path)
    print(f"Saved {len(serp_selected_offers)} selected offer groups to: {selected_output_path}")
    print(f"Saved {len(serp_skipped_offers)} skipped offer groups to: {skipped_output_path}")




"""

{
  "query_text": "1Password security features",
  "buyer_intent_score": 0.42,
  "serp_selection_status": "SKIPPED_INTENT_TOO_WEAK",
  "serp_selection_reason": "Buyer intent score below 0.50",
  "selected_for_serp": false
}
"""
