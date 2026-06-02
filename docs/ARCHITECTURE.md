# System Architecture

The **Agentic Drink Cart Placement Optimizer** is built around a single autonomous
agent (OpenAI Responses API, `gpt-4o-mini`) that runs a 7-step loop: it decides
which tools to call, iterates when data is incomplete, and self-corrects via a
runtime validator before producing the final placement plan.

## Diagram (renders on GitHub)

```mermaid
flowchart TD
    I1["Target date + number of carts"]
    I2["OpenAI key + Google Maps key"]

    I1 --> AGENT
    I2 --> AGENT

    AGENT["Agentic loop: OpenAI Responses API (gpt-4o-mini)<br/>autonomously selects tools, iterates, self-corrects via a runtime validator"]

    AGENT --> S1["1. Web Search<br/>OpenAI web_search_preview"]
    S1 --> S2["2. Extract and Parse<br/>Google Geocoding API + Open-Meteo"]
    S2 --> S3["3. Foot-Traffic Model<br/>sklearn LinearRegression"]
    S3 --> S4["4. RAG - Internal Data<br/>carts.json + zone_spots.json"]
    S4 --> S5["5. Foot-Traffic Map<br/>Google Maps JS + deck.gl"]
    S5 --> S6["6. Non-Linear Optimizer<br/>custom Python brute-force NLP"]
    S6 --> OUT["7. Placement Plan - Streamlit UI<br/>KPI band, table, interactive map, per-cart reasoning"]

    OUT -.->|"agent re-runs the loop / validator forces a retry"| AGENT

    classDef llm fill:#ede9fe,stroke:#7c3aed,color:#5b21b6;
    classDef google fill:#dbeafe,stroke:#2563eb,color:#1e40af;
    classDef data fill:#dcfce7,stroke:#16a34a,color:#166534;
    classDef input fill:#f1f5f9,stroke:#475569,color:#334155;
    classDef output fill:#ffedd5,stroke:#ea580c,color:#9a3412;

    class AGENT,S1 llm;
    class S2,S5 google;
    class S3,S4,S6 data;
    class I1,I2 input;
    class OUT output;
```

## Static image (for slides / reports)

A scalable vector version lives at [`architecture.svg`](architecture.svg) — open it
in any browser, or embed it directly:

![Architecture diagram](architecture.svg)

## Colour key

| Colour | Meaning |
|---|---|
| 🟪 Purple | LLM / agent orchestration (OpenAI) |
| 🟦 Blue | Google APIs (Geocoding, Places, Routes, Maps JS) |
| 🟩 Green | Data / ML / Python (regression, RAG store, optimizer) |
| ⬜ Slate | User input from the sidebar |
| 🟧 Orange | Final deliverable (the placement plan) |

## Notes

- **Weather** comes from **Open-Meteo** (free, no key). For dates beyond ~16 days
  out it falls back to a Seattle seasonal average and labels the source accordingly.
- The **heat layer** is rendered by **deck.gl's `GoogleMapsOverlay`**, the supported
  successor to Google's deprecated `visualization.HeatmapLayer`; cart pins and zone
  centroids are native Google Maps markers.

## Regenerating the SVG

The diagram is generated from a small script so it stays in sync with the loop:

```bash
python docs/make_architecture_diagram.py
```

Edit the `STEPS` list in [`make_architecture_diagram.py`](make_architecture_diagram.py)
and re-run to update `architecture.svg`.
