# GoldenBridge

GoldenBridge is a pipeline for collecting affiliate offers, scoring them, generating acquisition-focused search queries, and enriching those queries with SERP data.

Right now the repo is centered on the CJ flow, with the SERP stage being built out as the current downstream demo.

## What The Project Does

At a high level, the project does this:

1. Scrape and export raw advertiser data from CJ.
2. Extract and normalize the raw data.
3. Map the normalized rows into GoldenBridge's internal offer shape.
4. Score offers to identify stronger affiliate opportunities.
5. Generate query candidates for promising offers.
6. Validate and buyer-intent score those queries.
7. Filter which queries are worth SERP analysis.
8. Enrich the selected queries with live search results.

## Main Pipelines

### 1. CJ Offer Pipeline

Main entrypoint:

- [src/scripts/main.py](/home/paul/Paul/Projects/GoldenBridge/src/scripts/main.py:1)

This pipeline currently:

1. exports CJ HTML
2. extracts normalized rows
3. maps rows into internal offer objects
4. scores offers
5. builds top-offer outputs
6. builds category-cluster outputs

Main output areas:

- `data/raw/`
- `data/normalized/`
- `data/processed/`
- `data/scored/`
- `data/output/`

### 2. Query Candidate Pipeline

Relevant files:

- [src/services/queries_services/query_generation_service.py](/home/paul/Paul/Projects/GoldenBridge/src/services/queries_services/query_generation_service.py:1)
- [src/services/queries_services/query_validator_service.py](/home/paul/Paul/Projects/GoldenBridge/src/services/queries_services/query_validator_service.py:1)
- [src/scoring/buyer_intent_scoring.py](/home/paul/Paul/Projects/GoldenBridge/src/scoring/buyer_intent_scoring.py:1)

This stage takes scored offers and turns them into search-query candidates for content and acquisition work.

Current flow:

```text
generated
-> validated
-> buyer_intent_scored
```

Main output area:

- `data/query_candidates/`

### 3. SERP Enrichment Pipeline

Relevant files:

- [src/services/serp/filter_top_queries_for_serp_service.py](/home/paul/Paul/Projects/GoldenBridge/src/services/serp/filter_top_queries_for_serp_service.py:1)
- [src/services/serp/create_serp_input_objects_service.py](/home/paul/Paul/Projects/GoldenBridge/src/services/serp/create_serp_input_objects_service.py:1)
- [src/services/serp/README.md](/home/paul/Paul/Projects/GoldenBridge/src/services/serp/README.md:1)

This stage filters query candidates and enriches the selected ones with top Google results using SerpApi.

Current flow:

```text
buyer_intent_scored
-> serp_selected / serp_skipped
-> serp_input
```

Current demo end-state:

- [data/query_candidates/serp/serp_input/cj/advertisers/21-06-2026/14-07-26.json](/home/paul/Paul/Projects/GoldenBridge/data/query_candidates/serp/serp_input/cj/advertisers/21-06-2026/14-07-26.json)

Example shape from `serp_input`:

```json
[
  {
    "platform_id": "cj",
    "offer_id": "3812192",
    "name": "(IS) Interserver Webhosting and VPS",
    "queriesCandidates": [
      {
        "query": "Is Interserver worth it for small business hosting?",
        "query_type": "problem_aware",
        "buyer_intent_score": 0.75,
        "asset_type_recommendation": "review_page",
        "serp_selection_status": "validated",
        "serp_results": [
          {
            "position": 1,
            "title": "Anyone used Interserver? : r/webhosting",
            "url": "https://www.reddit.com/r/webhosting/comments/kq6ngc/anyone_used_interserver/",
            "domain": "www.reddit.com",
            "snippet": "Interserver is a well respected company, they have been in business for more than a decade."
          }
        ]
      }
    ]
  }
]
```

## Repo Structure

```text
src/
├── connectors/
│   └── cj/
├── scoring/
├── scripts/
└── services/
    ├── queries_services/
    └── serp/

data/
├── raw/
├── normalized/
├── processed/
├── scored/
├── output/
└── query_candidates/
```

## Setup

Create the environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install
```

## Environment Variables

The repo currently uses `.env` for API keys and credentials.

Examples already used by the code:

- `CJ_EMAIL`
- `CJ_PASSWORD`
- `CHAT_GPT_API_KEY`
- `QUERY_GENERATION_MODEL`
- `BUYER_INTENT_MODEL`
- `SERP_API_KEY`

## How To Run

Run the CJ pipeline:

```bash
.venv/bin/python -m src.scripts.main
```

Run query validation:

```bash
.venv/bin/python src/services/queries_services/query_validator_service.py
```

Run buyer-intent scoring:

```bash
.venv/bin/python src/scoring/buyer_intent_scoring.py
```

Run SERP filtering:

```bash
.venv/bin/python src/services/serp/filter_top_queries_for_serp_service.py
```

Run SERP enrichment:

```bash
.venv/bin/python src/services/serp/create_serp_input_objects_service.py
```

## Current State

- The CJ connector is the main ingestion path right now.
- Offer scoring and ranking outputs are already wired.
- Query generation and validation are present and producing staged JSON outputs.
- SERP enrichment is currently the active downstream demo, with `serp_input` as the current handoff format.

## Notes

- Some scripts still use fixed input paths while the pipeline is being built out.
- The SERP flow currently uses SerpApi instead of browser scraping.
- If you want the SERP-specific details, see [src/services/serp/README.md](/home/paul/Paul/Projects/GoldenBridge/src/services/serp/README.md:1).
