# General Topology EntityStore Web Application

An interactive topological knowledge graph, textbook explorer, and canonical property summary grid based on James Munkres' *Topology* (2nd Edition, 2000, Prentice Hall), using data extracted from the Wolfram Language data repository resource `"General Topology EntityStore"`.

---

## 1. Data Ingestion & Database Design

- **Source:** Extracted from `ResourceObject["General Topology EntityStore"]` (`General-Topology-EntityStore.wl`).
- **Entity Types:**
  - **`GeneralTopologyConcept`** (216 concepts): Foundational topological definitions including spaces, connectivity, compactness, separation axioms, and metric structures.
  - **`GeneralTopologyTheorem`** (225 theorems): Classical theorems from Munkres' *Topology*, including Urysohn's Lemma, Tychonoff's Theorem, Baire Category Theorem, and Ascoli's Theorem.
- **Relational & Graph SQLite Database (`backend/topology.db`):**
  - **`entities` Table:** Stores normalized fields including canonical ID, type (`concept` or `theorem`), friendly label, alternate names, qualifying objects, notation, restrictions, statement formula, references, and complete JSON summary grid rows.
  - **`relationships` Table:** Stores 1,659 directional relationships (`source_id`, `source_type`, `target_id`, `target_type`, `rel_type`) mapping connections between Concepts-to-Concepts, Theorems-to-Theorems, and Concepts-to-Theorems from `RelatedConcepts` and `RelatedTheorems` associations. Includes a composite index `idx_rel_source_target(source_id, target_id)` so graph queries (`WHERE source_id IN (...) AND target_id IN (...)`) filter directly inside SQLite for optimal scalability.

---

## 2. Formatting & LaTeX Rendering

- **Wolfram Box AST to Standard LaTeX Conversion:** A custom recursive AST parser (`backend/build_db.py`) parses Wolfram Language `TraditionalForm` box structures (`FormBox`, `TagBox`, `TemplateBox`, `GridBox`, `SubscriptBox`, `SuperscriptBox`, unicode mathematical symbols, etc.) and converts them into clean, textbook-standard LaTeX.
- **Traditional Math Form:** All formulas display in standard textbook notation rather than programming syntax.
- **MathJax 3 Integration:** Crisp client-side typesetting for all inline math (`$...$`) and multi-line equations (`\\[...\\]` and `\begin{array}...\end{array}`).

---

## 3. Frontend Pages & UI Layout

- **Home Page / Relationship Graph (`/`):**
  - Interactive node-link graph visualization using **Cytoscape.js** with force-directed CoSE layout.
  - **Color-coded Nodes:** Concepts are light green (`#B2FFB2`) and Theorems are light yellow (`#FFFF80`) to mirror the reference Munkres graph style.
  - **Interactive Controls:** Zoom in/out, fit to view, re-layout (`cose`, `grid`, `circle`, `concentric`), filter by type (`All (441)`, `Concepts (216)`, `Theorems (225)`), and instant search highlighting.
  - Clicking a node opens an instant inspector drawer with LaTeX statement preview and a direct link to visit the entity's dedicated summary page. Double-clicking navigates immediately.
- **Entity Explorer (`/explorer`):**
  - Scannable card grid view and structured table view of all 441 concepts and theorems.
  - Real-time search across names, identifiers, statement formulas, restrictions, alternate names, and citations.
  - Instant sorting and filtering by entity type.
- **Entity Detail Pages (`/entity/:id`):**
  - Renders the canonical **Munkres Summary Grid View** properties table replicating the structured row format shown in Munkres' topology documentation:
    - **Row headers (left column, `#FEF9C3` pale cream background):** Theorem/Math, Label, AlternateNames, QualifyingObjects, Notation, Restrictions, Statement/Expression, References, RelatedConcepts, RelatedTheorems.
    - **Value fields (right column):** Styled clean text with MathJax rendering for any mathematical statement, notation, or restriction constraint.
  - **Bidirectional Relationships:** Displays both outgoing referenced concepts/theorems AND incoming referenced-by connections as clickable color-coded badges (`#B2FFB2` green for concepts, `#FFFF80` yellow for theorems).
- **About Dataset (`/about`):**
  - Detailed documentation of the Munkres dataset, database architecture, and Summary Grid table fields.

---

## 4. Tech Stack & Running the App

- **Backend:** Python 3 + FastAPI + SQLite (`backend/app.py`). Serves API endpoints (`/api/stats`, `/api/graph`, `/api/entities`, `/api/entity/:id`, `/api/search`) and static production frontend bundle (`frontend/dist`).
- **Frontend:** React 19 + Vite + Tailwind CSS v4 + Cytoscape.js + MathJax 3.

### Quickstart

The server runs on port `3000`:

```bash
# Rebuild database (optional, pre-built topology.db is included)
python3 backend/build_db.py

# Rebuild frontend bundle (optional, pre-built frontend/dist is included)
cd frontend && npm install && npm run build && cd ..

# Start full-stack application
python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 3000
```
