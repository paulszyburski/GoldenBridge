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
    "review_page",
    "supporting_info_page",
    "comparison_page",
    "pricing_breakdown",
    "problem_asset",
    "utility_asset",
    "scorecard_asset",
    "checklist_asset",
    "calculator_asset",
    "alternatives_page",
}

COMMERCIAL_INTENT_HINTS = {
    "low",
    "medium",
    "high",
    "unknown",
}

BUYER_INTENT_REASON_CODES = {
    "INTENT_PURCHASE",
    "INTENT_COMPARISON",
    "INTENT_PRICING",
    "INTENT_INFORMATIONAL",
    "INTENT_PROBLEM",
    "INTENT_TOO_WEAK",
    "None"
}

QUERY_CANDIDATE_COUNT = 8
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
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def export_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def extract_processed_json(path, offer_id):
    if path not in _PROCESSED_JSON_CACHE:
        _PROCESSED_JSON_CACHE[path] = import_json(path)

    data = _PROCESSED_JSON_CACHE[path]
    for item in data:
        if (
            item.get("id") == offer_id
            or item.get("offer_id") == offer_id
            or item.get("partner_id") == offer_id
            or item.get("source_row_id") == offer_id
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

def _build_query_candidate(offer, candidate=None):
    candidate = candidate or {}
    query = candidate.get("query") or candidate.get("query_text")

    return {
        "offer_candidate_id": offer.get("offer_id"),
        "query": query,
        "query_type": candidate.get("query_type"),
        "persona": candidate.get("persona"),
        "problem": candidate.get("problem"),
        "target_market": offer.get("target_markets_processed"),
        "language": "en",
        "comparison_offer": candidate.get("comparison_offer"),
        "known_competitor_used": candidate.get("known_competitor_used"),
        "commercial_intent_hint": candidate.get("commercial_intent_hint"),
        "buyer_intent_score": None,
        "buyer_intent_reason_code": None,
        "negative_claim_evidence_required": candidate.get("negative_claim_evidence_required"),
        "human_layer_idea": candidate.get("human_layer_idea"),
        "ai_layer_idea": candidate.get("ai_layer_idea"),
        "llm_confidence": candidate.get("llm_confidence"),
        "asset_type_recommendation": candidate.get("asset_type_recommendation"),
        "primary_offer": offer.get("offer_name"),
        "status": "generated" if query else "needs_check",
        "notes": candidate.get("notes"),
    }

def _normalize_query_candidates(metadata, offer):
    if isinstance(metadata, dict):
        raw_candidates = metadata.get("queriesCandidates", [])
    elif isinstance(metadata, list):
        raw_candidates = metadata
    else:
        raw_candidates = []

    candidates = []

    for raw_candidate in raw_candidates[:QUERY_CANDIDATE_COUNT]:
        candidate = raw_candidate if isinstance(raw_candidate, dict) else None
        candidates.append(_build_query_candidate(offer, candidate))

    while len(candidates) < QUERY_CANDIDATE_COUNT:
        candidates.append(_build_query_candidate(offer))

    return candidates

def generate_offer_query_candidates(offer, reason_codes=None):
    cache_key = json.dumps(offer, sort_keys=True, default=str)
    if cache_key in _QUERY_GENERATION_CACHE:
        return _QUERY_GENERATION_CACHE[cache_key]

    prompt = f"""
    Given the following offer details, generate {QUERY_CANDIDATE_COUNT} distinct marketing search query candidates.
    Keep outputs short and practical.
    Mention the brand when the query is branded, comparative, pricing, review, alternatives, or negative-intent.
    If something is not clear, use null.

    here are the instructions for each field in the output:
    query_text:
    // Generate a natural EN-US search query a real buyer would type.
    // Prefer buying, comparison, pricing, alternatives, use-case, or problem-aware intent.
    // Avoid generic, navigational, support, login, or post-purchase queries.
    // These are supposed to be aquissition-focused queries that indicate a real interest in purchasing the product, not support/post purchase queries.
    // do not use the years in the query cuz u might get outdated, just keep it timeless, for example instead of "best CRM 2024" -> "best CRM for small business"
    // i repeat. do not use years in the query nor any dates.

    persona:
    // Identify the likely buyer/user behind the query.
    // Use a specific short label, e.g. "small business owner", "agency owner", "sales manager".
    // Use null only if genuinely unclear; avoid vague labels like "users" or "customers".

    problem:
    // Describe the practical problem or decision behind the search.
    // Make it useful for content planning, e.g. "compare cheaper CRM options before purchase".
    // Use null only if no clear problem can be inferred; avoid generic text like "wants information".

    known_competitor_used:
    // True If the query likely indicates comparison between two brands/products like "Intersever vs Bluehost" else False.

    comparison_offer:
    // If there is a clear comparison between the offer and some competitor in the query then set the comparison offer as the name od the competitor in the query
    // example query: "Interserver vs Bluehost" -> comparison_offer: "Bluehost"
    // if there is no clear comparison, or if the query is not comparative, set this field to None
    // Do not set some competitor if its not in the query, for example "best VPS hosting for developers" should not have a comparison_offer even if Interserver has known competitors in the VPS hosting space, because the query does not explicitly mention any of them
    // if the query doesnt mention a competitor set it as None
    

    commercial_intent_hint:
    // Provide a commercial intent hint of "low", "medium", "high", or "unknown" based on your quick rough guess of commercial intent

    negative_claim_evidence_required:
    // if the query seems to indicate a negative claim against the offer (eg. "Interserver VPS limitations" when the offer is Interserver) set the negative_claim_evidence_required to True, else False or null if unclear

    human_layer_idea:
    // Suggest one practical page component that would make a human user click, stay, or use the asset.
    // Prefer calculators, scorecards, checklists, comparison tables, quizzes, decision trees, or plan selectors.
    // Keep it short and specific to the query.

    ai_layer_idea:
    // Suggest structured content that would help AI/search systems understand and cite the asset.
    // Prefer Q&A blocks, comparison tables, pricing summaries, methodology notes, pros/cons tables, freshness indicators, or evidence-backed matrices.
    // Keep it short and specific to the query.

    llm_confidence:
    // provide a confidence on how the relevant/useful and well formed the query is
    // Use:
    // "high" if the query is very relevant, well formed, and seems like something a real buyer would search for
    // "medium" if the query is somewhat relevant and well formed but could be improved
    // "low" if the query is not very relevant, poorly formed, or doesn't seem like something a real buyer would search for

    Return valid JSON only in this shape:
    {{
        "queriesCandidates": [
            {{
                "query": "...",
                "query_type": "...",
                "persona": "...",
                "problem": "...",
                "known_competitor_used": "...",
                "comparison_offer": "...",
                "commercial_intent_hint": "...",
                "negative_claim_evidence_required": ...,
                "human_layer_idea": "...",
                "ai_layer_idea": "...",
                "llm_confidence": "...",
                "asset_type_recommendation": "...",
                "notes": "..."
            }}
        ]
    }}

    queriesCandidates must contain exactly {QUERY_CANDIDATE_COUNT} objects.
    Include "comparison_offer" only for comparison query objects.
    query_type must be one of: {", ".join(QUERY_TYPES)}
    asset_type_recommendation must be one of: {", ".join(ASSET_TYPE_RECOMMENDATIONS)}

    Offer details: {offer}
    """
    raw_response = generate_response_from_gpt(prompt, max_tokens=5500)

    try:
        metadata = _parse_json_response(raw_response)
    except json.JSONDecodeError:
        if reason_codes is not None:
            reason_codes.append("invalid_ai_json")
        metadata = {}

    result = _normalize_query_candidates(metadata, offer)
    _QUERY_GENERATION_CACHE[cache_key] = result
    return result

def generate_intent_stage(offer, reason_codes):
    return None

def generate_query_candidate(offer, source_path):
    reason_codes = []

    platform_id = offer.get("platform_id", "Unknown")
    offer_id = offer.get("offer_id", "Unknown")
    name = offer.get("name") or offer.get("offer_name", "Unknown")
    queries_candidates = generate_offer_query_candidates(offer, reason_codes)

    return {
        "platform_id": platform_id, 
        "offer_id": offer_id,
        "name": name,
        "queriesCandidates": queries_candidates,
        "source_file": source_path,
    }

def generate_query_candidates(offers, source_path):
    query_candidates = []
    for i, offer in enumerate(offers):
        print(i)
        if i == 1:
            break
        if offer["scoring_status"] != "scoreable_basic":
            print(f"Offer with id {offer.get('offer_id')} has scoring status {offer['scoring_status']}, skipping GPT generation.")
            continue

        source_row_id = offer.get("source_offer_ref").get("source_row_id")
        extracted_offer = extract_processed_json(source_path, source_row_id)
        if extracted_offer is None:
            print(f"No processed data found for offer with id {source_row_id}, skipping GPT generation.")
            continue
        candidate = generate_query_candidate(extracted_offer, source_path)
        query_candidates.append(candidate)

    return query_candidates

if __name__ == "__main__":
    now = datetime.now().strftime("%H-%M-%S")
    today = datetime.now().strftime("%d-%m-%Y")
    input_path = f"data/scored/cj/advertisers/07-06-2026/12-44-38.json"
    output_path = f"data/query_candidates/generated/cj/advertisers/{today}/{now}.json"
    source_path = f"data/processed/cj/advertisers/{today}/12-44-38.json"
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
