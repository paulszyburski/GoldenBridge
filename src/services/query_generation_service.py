import json
from dotenv import load_dotenv
from typing import Any, Dict, List

# from openai import OpenAI

load_dotenv()


def import_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def export_json(data, path):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def extract_processed_json(path, id):
    data = import_json(path)
    for item in data:
        if (
            item.get("id") == id
            or item.get("offer_id") == id
            or item.get("partner_id") == id
            or item.get("source_row_id") == id
        ):
            return item
    return None

def convert_target_markets(target_markets):
    modified_target_markets = []
    if not target_markets:
        return []
    normalized = {str(x).strip().upper() for x in target_markets}
    if "U.S." in normalized or "UNITED STATES" in normalized or "USA" in normalized:
        modified_target_markets.append("EN-US")
    if "U.K." in normalized or "UNITED KINGDOM" in normalized or "UK" in normalized:
        modified_target_markets.append("EN-GB")
    if "CANADA" in normalized:
        modified_target_markets.append("EN-CA")
    return modified_target_markets

def _template_candidates(row: Dict[str, Any], target_markets: List[str]) -> List[Dict[str, Any]]:
    offer_name = row.get("offer_name", "Offer")
    category = row.get("category", "software")
    market = target_markets[0] if target_markets else "EN-US"
    offer_id = str(row.get("offer_id", ""))
    platform_id = str(row.get("platform_id", ""))
    partner_id = str(row.get("partner_id", ""))
    base = {
        "offer_id": offer_id,
        "platform_id": platform_id,
        "partner_id": partner_id,
        "target_market": market,
        "base_category": category,
        "persona": "placeholder persona",
        "problem": f"placeholder problem for {category.lower()}",
        "use_case": "placeholder use case",
        "buyer_intent_estimate": "high",
        "recommended_asset_type": "comparison_page",
        "dual_engine_human_component": "placeholder human component",
        "dual_engine_ai_component": "placeholder ai component",
        "source": "dummy_generated",
        "status": "generated",
        "reason_codes": []
    }
    return [
        {
            **base,
            "query": f"best {category.lower()} placeholder query",
            "query_type": "best_for",
        },
        {
            **base,
            "query": f"{offer_name} alternatives placeholder",
            "query_type": "alternatives",
        },
    ]

def _generate_with_chatgpt(row: Dict[str, Any], target_markets: List[str]):
    # Dummy mode only: ChatGPT generation is disabled to avoid API costs.
    #
    # if not gpt_api or OpenAI is None:
    #     return _template_candidates(row, target_markets), "template_generated"
    #
    # client = OpenAI(api_key=gpt_api)
    # prompt = (
    #     "Generate 2 high-intent SEO query candidates for an affiliate offer.\n"
    #     "Return JSON only as an array of objects.\n"
    #     "Each object must include: "
    #     "query, query_type, target_market, base_category, persona, problem, use_case, "
    #     "buyer_intent_estimate, recommended_asset_type, dual_engine_human_component, "
    #     "dual_engine_ai_component.\n"
    #     "query_type should be one of: best_for, alternatives.\n"
    #     "buyer_intent_estimate should be low|medium|high.\n"
    #     f"Offer data: {json.dumps(row, ensure_ascii=False)}\n"
    #     f"Allowed target markets: {json.dumps(target_markets)}"
    # )
    # response = client.responses.create(
    #     model=os.getenv("CHAT_GPT_MODEL", "gpt-4.1-mini"),
    #     temperature=0.4,
    #     input=prompt,
    # )
    # raw_text = (response.output_text or "").strip()
    # try:
    #     parsed = json.loads(raw_text)
    #     if isinstance(parsed, list):
    #         return parsed, "chat_gpt_generated"
    # except json.JSONDecodeError:
    #     pass
    # return _template_candidates(row, target_markets), "template_generated"
    return _template_candidates(row, target_markets), "dummy_generated"

def generate_query_candidate(row):
    if not row:
        return {
            "platform_id": None,
            "partner_id": None,
            "offer_id": None,
            "offer_name": None,
            "status": "error",
            "reason_codes": ["SOURCE_ROW_NOT_FOUND"],
            "query_candidates": [],
        }

    target_markets = convert_target_markets(row.get("target_markets", []))
    generated, source = _generate_with_chatgpt(row, target_markets)

    candidates = []
    for item in generated[:2]:
        candidates.append(
            {
                "offer_id": row.get("offer_id"),
                "platform_id": row.get("platform_id"),
                "partner_id": row.get("partner_id"),
                "query": item.get("query"),
                "query_type": item.get("query_type"),
                "target_market": item.get("target_market") or (target_markets[0] if target_markets else "EN-US"),
                "base_category": item.get("base_category") or row.get("category"),
                "persona": item.get("persona"),
                "problem": item.get("problem"),
                "use_case": item.get("use_case"),
                "buyer_intent_estimate": item.get("buyer_intent_estimate", "high"),
                "recommended_asset_type": item.get("recommended_asset_type", "comparison_page"),
                "dual_engine_human_component": item.get("dual_engine_human_component", "comparison scorecard"),
                "dual_engine_ai_component": item.get("dual_engine_ai_component", "Q&A blocks + comparison table + methodology note"),
                "source": source,
                "status": "generated",
                "reason_codes": [],
            }
        )
    return {
        "platform_id": row.get("platform_id"),
        "partner_id": row.get("partner_id"),
        "offer_id": row.get("offer_id"),
        "offer_name": row.get("offer_name"),
        "status": "generated",
        "reason_codes": [],
        "query_candidates": candidates,
    }


def main(data):
    modified_data = []
    for row in data:
        processed_row_path = row["source_offer_ref"]["processed_source_file"]
        processed_row = extract_processed_json(processed_row_path, row["offer_id"])

        query_candidate = generate_query_candidate(processed_row)
        modified_data.append(query_candidate)
    return modified_data


if __name__ == "__main__":
    input_data = import_json("data/scored/cj/advertisers/30-05-2026/15-20-02.json")
    output = main(input_data)
    export_json(output, "output_data.json")
