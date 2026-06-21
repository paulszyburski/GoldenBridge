import os
import json
from datetime import datetime
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen
from urllib.error import HTTPError
from dotenv import load_dotenv


load_dotenv()

SERP_API_URL = "https://serpapi.com/search.json"
SERP_API_KEY = os.getenv("SERP_API_KEY") or os.getenv("SERPAPI_API_KEY")
SERP_LOCATION = "Austin, Texas, United States"
SERP_LANGUAGE = "en"
SERP_COUNTRY = "us"
SERP_GOOGLE_DOMAIN = "google.com"
TEST_SERP_SELECTED_PATH = (
    "data/query_candidates/serp/serp_selected/cj/advertisers/21-06-2026/12-31-39.json"
)


def import_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def export_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def search_top_results(query, top_n=5):
    if not SERP_API_KEY:
        raise ValueError("Missing SERP API key. Set SERP_API_KEY in .env.")

    params = {
        "q": query,
        "location": SERP_LOCATION,
        "hl": SERP_LANGUAGE,
        "gl": SERP_COUNTRY,
        "google_domain": SERP_GOOGLE_DOMAIN,
        "api_key": SERP_API_KEY,
    }
    url = f"{SERP_API_URL}?{urlencode(params)}"

    try:
        with urlopen(url) as response:
            data = json.load(response)
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"SerpApi request failed with HTTP {error.code}: {error_body}"
        ) from error

    results = []
    organic_results = data.get("organic_results", [])

    for item in organic_results[:top_n]:
        result_url = item.get("link")
        results.append({
            "position": item.get("position"),
            "title": item.get("title"),
            "url": result_url,
            "domain": urlparse(result_url).netloc if result_url else None,
            "snippet": item.get("snippet"),
        })

    return results

def create_serp_input_object(query_candidate):
    top_results = search_top_results(query_candidate["query"])
    query_candidate["serp_results"] = top_results
    return query_candidate

def create_serp_input_objects(data):
    modified_data = []
    for offer in data:
        serp_input_objects = []
        for query_candidate in offer["queriesCandidates"]:
            serp_input_object = create_serp_input_object(query_candidate)
            serp_input_objects.append(serp_input_object)

        offer["queriesCandidates"] = serp_input_objects
        modified_data.append(offer)
    return modified_data



if __name__ == "__main__":
    now = datetime.now().strftime("%H-%M-%S")
    today = datetime.now().strftime("%d-%m-%Y")
    output_path = f"data/query_candidates/serp/serp_input/cj/advertisers/{today}/{now}.json"

    offers = import_json(TEST_SERP_SELECTED_PATH)
    test_data = create_serp_input_objects(offers[:1])
    export_json(test_data, output_path)
    print(f"Saved test SERP input objects to: {output_path}")
