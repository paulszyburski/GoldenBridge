# CJ Connector

This folder contains the CJ-specific ingestion connector for Gold Bridge.

The purpose of this connector is to collect advertiser/program data from CJ, preserve the raw source data, normalize it into Gold Bridge’s internal `OfferCandidate` format, and pass it to the scoring pipeline.

The CJ connector does **not** decide whether an offer is good or bad.  
It only collects, parses, and maps data.

Scoring, rejection, hard blockers, and business decisions happen outside this folder.

---

## Core Rule

```text
CJ connector = collect and normalize
Scoring engine = decide
Operator = final Human Gate