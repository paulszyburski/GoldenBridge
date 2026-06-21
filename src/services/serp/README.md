# SERP Pipeline

This folder contains the current SERP enrichment flow for query candidates.

Right now the goal is simple:

1. Filter query candidates down to the ones worth checking in search.
2. Fetch top Google results for those selected queries.
3. Save the enriched output into the `serp_input` data folder.

For now, `serp_input` is the current end of the process and acts as the demo output for this pipeline.

## Current Files

- `filter_top_queries_for_serp_service.py`
  Filters `buyer_intent_scored` query candidates into:
  - `serp_selected`
  - `serp_skipped`

- `create_serp_input_objects_service.py`
  Reads `serp_selected`, calls the SerpApi endpoint, and adds `serp_results` to each selected query candidate.

## Current Data Flow

```text
buyer_intent_scored
-> serp_selected / serp_skipped
-> serp_input
```

## Output Folders

```text
data/query_candidates/serp/
├── serp_selected/
├── serp_skipped/
└── serp_input/
```

## What `serp_input` Contains

Each query candidate in `serp_input` keeps its original metadata and gains:

- `serp_results`

Each `serp_results` item currently contains:

- `position`
- `title`
- `url`
- `domain`
- `snippet`

## Demo Output

Current demo output example:

- [14-07-26.json](/home/paul/Paul/Projects/GoldenBridge/data/query_candidates/serp/serp_input/cj/advertisers/21-06-2026/14-07-26.json)

That file shows the current end-state of this SERP flow: selected query candidates enriched with top search results and saved under `data/query_candidates/serp/serp_input/...`.

## How To Run

Filter candidates:

```bash
.venv/bin/python src/services/serp/filter_top_queries_for_serp_service.py
```

Create SERP input objects:

```bash
.venv/bin/python src/services/serp/create_serp_input_objects_service.py
```

## Notes

- `create_serp_input_objects_service.py` currently uses `SERP_API_KEY` from `.env`.
- The test block in `create_serp_input_objects_service.py` currently reads one `serp_selected` file and writes one `serp_input` file.
- The pipeline is still in a demo / build-out stage. `serp_input` is the current final handoff format for the next step.
