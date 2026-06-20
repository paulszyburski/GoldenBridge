import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

gpt_api = os.getenv("CHAT_GPT_API_KEY", None)
gpt_model = os.getenv("BUYER_INTENT_MODEL", "gpt-4.1-nano")
client = OpenAI(api_key=gpt_api) if gpt_api else None

def import_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def export_json(path, data):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data

def _parse_json_response(raw_response):
    cleaned_response = raw_response.strip()
    if cleaned_response.startswith("```"):
        cleaned_response = cleaned_response.strip("`")
        if cleaned_response.startswith("json"):
            cleaned_response = cleaned_response[4:].strip()

    return json.loads(cleaned_response)

def score_buyer_intents_for_offer(queryCandidates):
    if client is None:
        raise ValueError("CHAT_GPT_API_KEY is not set.")

    candidate_payload = []
    for queryCandidate in queryCandidates:
        candidate_payload.append({
            "query": queryCandidate.get("query"),
            "query_type": queryCandidate.get("query_type"),
            "persona": queryCandidate.get("persona"),
            "problem": queryCandidate.get("problem"),
            "commercial_intent_hint": queryCandidate.get("commercial_intent_hint"),
            "primary_offer": queryCandidate.get("primary_offer"),
            "comparison_offer": queryCandidate.get("comparison_offer"),
        })

    response = client.responses.create(
        model=gpt_model,
        input=
        f"""
        Score the buyer intent for each query candidate below.
        Return ONLY valid JSON in this exact shape:
        {{"scores": [0.86, 0.42]}}

        Rules:
        - each score must be a number between 0 and 1
        - keep the same order as the input list
        - do not include explanations
        - use decimal numbers, not strings

        Query candidates:
        {json.dumps(candidate_payload, ensure_ascii=False)}
        """,
        max_output_tokens=120,
    )

    parsed_response = _parse_json_response(response.output_text)
    return parsed_response.get("scores", [])

def score_buyer_intents(data):
    modified_data = []
    for i, offer in enumerate(data[0:1]):
        print(i)
        modified_query_candidates = []
        queryCandidates = offer["queriesCandidates"]
        scored_buyer_intents = score_buyer_intents_for_offer(queryCandidates)
        for index, queryCandidate in enumerate(queryCandidates):
            scored_buyer_intent = scored_buyer_intents[index] if index < len(scored_buyer_intents) else None
            queryCandidate["buyer_intent_score"] = float(scored_buyer_intent) if scored_buyer_intent is not None else None
            modified_query_candidates.append(queryCandidate)
        
        offer["queriesCandidates"] = modified_query_candidates
        modified_data.append(offer)

    return modified_data


if __name__ == "__main__":
    input_path = "data/query_candidates/validated/cj/advertisers/07-06-2026/15-35-58.json"
    output_path = "test.json"

    data = import_json(input_path)
    modified_data = score_buyer_intents(data)
    export_json(output_path, modified_data)
            
