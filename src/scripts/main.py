from datetime import datetime
import pprint
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.connectors.cj import export_html, extractor, mapper
from src.scoring import prelimitary_offer_scoring
from src.services import top_offers_service, category_cluster_service


def run_cj_pipeline(top_n=10):
    today = datetime.now().strftime("%d-%m-%Y")
    now = datetime.now().strftime("%H-%M-%S")
    extracted_at = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    raw_folder_path = f"data/raw/cj/advertisers/{today}"
    raw_html_path = f"{raw_folder_path}/{now}.html"
    normalized_path = f"data/normalized/cj/advertisers/{today}/{now}.json"
    processed_path = f"data/processed/cj/advertisers/{today}/{now}.json"
    scored_path = f"data/scored/cj/advertisers/{today}/{now}.json"

    print("[1/6] Exporting CJ HTML...")
    html = export_html.scrape_html()
    export_html.save_html(html, raw_html_path)
    print(f"Saved raw HTML: {raw_html_path}")

    print("[2/6] Extracting + normalizing raw rows...")
    normalized_rows = extractor.extract_from_raw_folder(raw_folder_path, extracted_at)
    extractor.save_json(normalized_rows, normalized_path)
    print(f"Saved normalized JSON: {normalized_path} ({len(normalized_rows)} rows)")

    print("[3/6] Mapping normalized rows...")
    normalized_json = mapper.import_json(normalized_path)
    mapped_rows = mapper.map_json(normalized_json, normalized_path)
    mapper.export_json(mapped_rows, processed_path)
    print(f"Saved processed JSON: {processed_path} ({len(mapped_rows)} rows)")

    print("[4/6] Scoring offers...")
    processed_json = prelimitary_offer_scoring.import_json(processed_path)
    scored_rows = prelimitary_offer_scoring.shape_json(processed_json, processed_path)
    prelimitary_offer_scoring.export_json(scored_path, scored_rows)
    print(f"Saved scored JSON: {scored_path} ({len(scored_rows)} rows)")

    print("[5/6] Building top offers outputs...")
    top_offers_service.generate_rankings(scored_rows, n=top_n, output_root="data/output")
    print("Saved: top_offers_overall, top_offers_by_category, best_category_clusters")

    print("[6/6] Building category cluster scores...")
    category_cluster_paths = category_cluster_service.generate_category_cluster_scores(
        scored_rows, output_root="data/output"
    )
    for path in category_cluster_paths:
        print(f"Saved category cluster scores: {path}")

    return {
        "raw_folder_path": raw_folder_path,
        "raw_html_path": raw_html_path,
        "normalized_path": normalized_path,
        "processed_path": processed_path,
        "scored_path": scored_path,
        "category_cluster_paths": category_cluster_paths,
        "rows": len(scored_rows),
    }


if __name__ == "__main__":
    result = run_cj_pipeline()
    print("Pipeline finished.")
    pprint.pprint(result)
