import json
import os
from dotenv import load_dotenv
from datetime import datetime

from openai import OpenAI

load_dotenv()

gpt_api = os.getenv("CHAT_GPT_API_KEY", None)
gpt_model = os.getenv("QUERY_GENERATION_MODEL", "gpt-4o-mini")

MODEL_PRICING_PER_1M = {
    "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-4.1-mini": {"input": 0.40, "cached_input": 0.10, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "cached_input": 0.025, "output": 0.40},
}

QUERY_TYPES = {
    "best_for",
    "vs",
    "alternatives",
    "pricing",
    "price_sensitive",
    "review",
    "comparison",
    "problem_aware",
    "negative_intent",
    "use_case",
    "persona_specific",
    "integration_specific",
    "informational",
}

ASSET_TYPE_RECOMMENDATIONS = {
    "comparison_page",
    "alternatives_page",
    "pricing_breakdown",
    "review_page",
    "problem_asset",
    "utility_asset",
    "scorecard_asset",
    "checklist_asset",
    "calculator_asset",
    "supporting_info_page",
}

_QUERY_GENERATION_CACHE = {}
_PROCESSED_JSON_CACHE = {}
_GPT_CLIENT = OpenAI(api_key=gpt_api) if gpt_api else None
_USAGE_TOTALS = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cached_input_tokens": 0,
    "total_tokens": 0,
    "requests": 0,
}

def import_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def export_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def extract_processed_json(path, id):
    if path not in _PROCESSED_JSON_CACHE:
        _PROCESSED_JSON_CACHE[path] = import_json(path)

    data = _PROCESSED_JSON_CACHE[path]
    for item in data:
        if (
            item.get("id") == id
            or item.get("offer_id") == id
            or item.get("partner_id") == id
            or item.get("source_row_id") == id
        ):
            return item
    return None

def generate_response_from_gpt(prompt, max_tokens=500):
    if _GPT_CLIENT is None:
        raise ValueError("CHAT_GPT_API_KEY is not set.")

    response = _GPT_CLIENT.chat.completions.create(
        model=gpt_model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens
    )
    usage = response.usage
    prompt_tokens_details = getattr(usage, "prompt_tokens_details", None)
    cached_tokens = getattr(prompt_tokens_details, "cached_tokens", 0) if prompt_tokens_details else 0

    _USAGE_TOTALS["input_tokens"] += getattr(usage, "prompt_tokens", 0)
    _USAGE_TOTALS["output_tokens"] += getattr(usage, "completion_tokens", 0)
    _USAGE_TOTALS["cached_input_tokens"] += cached_tokens
    _USAGE_TOTALS["total_tokens"] += getattr(usage, "total_tokens", 0)
    _USAGE_TOTALS["requests"] += 1

    return response.choices[0].message.content

def estimate_total_cost():
    pricing = MODEL_PRICING_PER_1M.get(gpt_model)
    if pricing is None:
        return None

    cached_input_tokens = _USAGE_TOTALS["cached_input_tokens"]
    non_cached_input_tokens = max(0, _USAGE_TOTALS["input_tokens"] - cached_input_tokens)

    input_cost = (non_cached_input_tokens / 1_000_000) * pricing["input"]
    cached_input_cost = (cached_input_tokens / 1_000_000) * pricing["cached_input"]
    output_cost = (_USAGE_TOTALS["output_tokens"] / 1_000_000) * pricing["output"]

    return input_cost + cached_input_cost + output_cost

def _parse_json_response(raw_response):
    cleaned_response = raw_response.strip()
    if cleaned_response.startswith("```"):
        cleaned_response = cleaned_response.strip("`")
        if cleaned_response.startswith("json"):
            cleaned_response = cleaned_response[4:].strip()

    return json.loads(cleaned_response)

def generate_query_metadata(offer, reason_codes=None):
    cache_key = json.dumps(offer, sort_keys=True, default=str)
    if cache_key in _QUERY_GENERATION_CACHE:
        return _QUERY_GENERATION_CACHE[cache_key]

    prompt = f"""
    Given the following offer details, generate marketing search metadata.
    Keep outputs short and practical.
    Do not mention the brand unless it is necessary to make the query natural.
    If something is not clear, use null.

    Return valid JSON only with these keys:
    "query_text", "query_type", "persona", "problem", "asset_type_recommendation"

    query_type must be one of: {", ".join(QUERY_TYPES)}
    asset_type_recommendation must be one of: {", ".join(ASSET_TYPE_RECOMMENDATIONS)}

    Offer details: {offer}
    """
    raw_response = generate_response_from_gpt(prompt, max_tokens=220)

    try:
        metadata = _parse_json_response(raw_response)
    except json.JSONDecodeError:
        if reason_codes is not None:
            reason_codes.append("invalid_ai_json")
        metadata = {}

    result = {
        "query_text": metadata.get("query_text"),
        "query_type": metadata.get("query_type"),
        "persona": metadata.get("persona"),
        "problem": metadata.get("problem"),
        "asset_type_recommendation": metadata.get("asset_type_recommendation"),
    }
    _QUERY_GENERATION_CACHE[cache_key] = result
    return result

def generate_intent_stage(offer, reason_codes):
    return None

def generate_query_candidate(offer, source_path):
    reason_codes = []

    platform_id = offer.get("platform_id", "Unknown")
    offer_id = offer.get("offer_id", "Unknown")
    name = offer.get("name") or offer.get("offer_name", "Unknown")
    metadata = generate_query_metadata(offer, reason_codes)
    query_text = metadata.get("query_text")
    query_type = metadata.get("query_type")
    persona = metadata.get("persona")
    problem = metadata.get("problem")
    intent_stage = generate_intent_stage(offer, reason_codes)
    asset_type_recommendation = metadata.get("asset_type_recommendation")
    primary_offer = offer.get("offer_name", "Unknown")
    target_markets = offer.get("target_markets_processed")
    source_file = source_path
    status = "generated" if reason_codes == [] else "needs_review"

    return {
        "platform_id": platform_id, 
        "offer_id": offer_id,
        "name": name,
        "query_text": query_text,
        "query_type": query_type,
        "target_markets": target_markets,
        "persona": persona,
        "problem": problem,
        "intent_stage": intent_stage,
        "asset_type_recommendation": asset_type_recommendation,
        "primary_offer": primary_offer,
        "status": status,
        "source_file": source_file,
        "reason_codes": reason_codes,
    }

def generate_query_candidates(offers, source_path):
    query_candidates = []
    for i, offer in enumerate(offers):
        if offer["scoring_status"] != "scoreable_basic":
            print(f"Offer with id {id} has scoring status {offer['scoring_status']}, skipping GPT generation.")
            continue

        id = offer.get("source_offer_ref").get("source_row_id")
        extracted_offer = extract_processed_json(source_path, id)
        if extracted_offer is None:
            print(f"No processed data found for offer with id {id}, skipping GPT generation.")
            continue
        candidate = generate_query_candidate(extracted_offer, source_path)
        query_candidates.append(candidate)
        if i == 10:
            break

    return query_candidates

if __name__ == "__main__":
    now = datetime.now().strftime("%H-%M-%S")
    today = datetime.now().strftime("%d-%m-%Y")
    input_path = f"data/scored/cj/advertisers/06-06-2026/20-56-46.json"
    output_path = f"data/query_candidates/cj/advertisers/{today}/{now}.json"
    source_path = f"data/processed/cj/advertisers/{today}/20-53-33.json"
    scored_offers = import_json(input_path)
    print(f"Generating query candidates for {len(scored_offers)} offers...")
    query_candidates = generate_query_candidates(scored_offers, source_path)
    print(f"Generated {len(query_candidates)} query candidates, exporting to JSON...")
    export_json(query_candidates, output_path)
    estimated_cost = estimate_total_cost()
    print(
        "Usage summary: "
        f"{_USAGE_TOTALS['requests']} request(s), "
        f"{_USAGE_TOTALS['input_tokens']} input tokens, "
        f"{_USAGE_TOTALS['output_tokens']} output tokens, "
        f"{_USAGE_TOTALS['total_tokens']} total tokens."
    )
    if estimated_cost is None:
        print(f"Estimated cost unavailable for model {gpt_model}. Add pricing to MODEL_PRICING_PER_1M to enable it.")
    else:
        print(f"Estimated cost for {gpt_model}: ${estimated_cost:.6f}")
