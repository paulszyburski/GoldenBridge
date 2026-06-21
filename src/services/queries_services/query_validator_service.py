import json
import os
from datetime import datetime


def import_json(path):
    with open(path, "r") as f:
        return json.load(f)

def export_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def validate_query_candidate(candidate):
    if candidate.get("target_market") != "EN-US": candidate["status"] = "rejected"
    if candidate.get("language") != "en": candidate["status"] = "rejected"
    if candidate.get("buyer_intent_score") != None: candidate["buyer_intent_score"] = None
    if candidate.get("buyer_intent_score_reason") != None: candidate["buyer_intent_score_reason"] = None
    if candidate.get("query_type") == "pricing": candidate["asset_type_recommendation"] = "pricing_breakdown"
    if candidate.get("query_type") == "alternatives": candidate["asset_type_recommendation"] = "alternatives_page"
    if candidate.get("query_type") == "vs": candidate["asset_type_recommendation"] = "comparison_page"
    if candidate.get("query_type") == "negative_intent": candidate["asset_type_recommendation"] = "review_page"
    if candidate.get("comparison_offer") != None:
        if candidate.get("comparison_offer").split()[0] not in candidate.get("query").split(): candidate["comparison_offer"] = None
    if candidate.get("comparison_offer") == None: candidate["known_competitor_used"] = None

    if candidate.get("status") != "rejected":
        candidate["status"] = "validated"

    return candidate

def validate_query_candidates(offers):
    validated_offers = []
    for offer in offers:
        validated_candidates = []
        for candidate in offer.get("queriesCandidates", []):
            validated_candidate = validate_query_candidate(candidate)
            validated_candidates.append(validated_candidate)

        
        validated_offer = {
            "platform_id": offer.get("platform_id"),
            "offer_id": offer.get("offer_id"),
            "name": offer.get("name"),
            "queriesCandidates": validated_candidates
        }
        validated_offers.append(validated_offer)

    return validated_offers


if __name__ == "__main__":
    today = datetime.now().strftime("%d-%m-%Y")
    now = datetime.now().strftime("%H-%M-%S")
    input_path = f"data/query_candidates/generated/cj/advertisers/{today}/21-02-40.json"
    output_path = f"data/query_candidates/validated/cj/advertisers/{today}/{now}.json"

    candidates = import_json(input_path)
    print(f"Validating {len(candidates)} query candidates...")
    validated_candidates = validate_query_candidates(candidates)
    export_json(validated_candidates, output_path)
    print(f"Saved {len(validated_candidates)} validated candidates to: {output_path}")
