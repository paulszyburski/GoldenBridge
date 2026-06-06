import json
import os
from dotenv import load_dotenv
from datetime import datetime

from openai import OpenAI

load_dotenv()

gpt_api = os.getenv("CHAT_GPT_API_KEY", None)

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

def import_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def export_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
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

def generate_response_from_gpt(prompt, max_tokens=500):
    client = OpenAI(api_key=gpt_api)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def generate_query(offer, reason_codes=None):
    prompt = f"""
    Given the following offer details, generate a search query that a potential customer might use when searching for this offer. The query shouldnt be too specific and it shouldnt look for a specific brand, just a vague query a potential customer will use. Offer details: {offer}

    """
    return generate_response_from_gpt(prompt)

def generate_query_type(query, reason_codes):
    prompt = f"""
    Given the following query {query}, generate the most suitable query type from the following list:
    {", ".join(QUERY_TYPES)}
    """
    return generate_response_from_gpt(prompt)

def generate_persona(offer, reason_codes):
    prompt = f"""
    Describe the most likely persona for a potential customer searching for this offer, based on the offer details. The description should be short but descriptive. Examples: "small business owner", "tech-savvy professional". If not clear use None. Offer details: {offer}
    """
    return generate_response_from_gpt(prompt)

def generate_problem(query, reason_codes):
    prompt = f"""
    Identify the main problem or pain point that this user that searched this query has. Example: "track leads without enterprise CRM complexity". If not clear use None. Query: {query}
    """
    return generate_response_from_gpt(prompt)

def generate_intent_stage(offer, reason_codes):
    return # TODO: implement in the future here or somehwere else

def generate_asset_type_recommendation(offer, reason_codes):
    prompt = f"""
    Choose exactly one content format that best fits this query. Do not choose based on what is easiest. Choose based on user intent. Select from the following list: {", ".join(ASSET_TYPE_RECOMMENDATIONS)}. If not clear use None. Offer details: {offer}
    """
    return generate_response_from_gpt(prompt)

def generate_query_candidate(offer, source_path):
    reason_codes = []

    platform_id = offer.get("platform_id", "Unknown")
    offer_id = offer.get("offer_id", "Unknown")
    name = offer.get("name") or offer.get("offer_name", "Unknown")
    query_text = generate_query(offer, reason_codes)
    query_type = generate_query_type(query_text, reason_codes)
    persona = generate_persona(offer, reason_codes)
    problem = generate_problem(query_text, reason_codes)
    intent_stage = generate_intent_stage(offer, reason_codes)
    asset_type_recommendation = generate_asset_type_recommendation(offer, reason_codes)
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
    for offer in offers:
        id = offer.get("source_offer_ref").get("source_row_id")
        extracted_offer = extract_processed_json(source_path, id)
        if extracted_offer is None:
            print(f"No processed data found for offer with id {id}, skipping GPT generation.")
            continue
        candidate = generate_query_candidate(extracted_offer, source_path)
        query_candidates.append(candidate)
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

