import os
import json
import sqlite3
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

DB_PATH = os.path.join(os.path.dirname(__file__), 'topology.db')

app = FastAPI(title="General Topology EntityStore API", version="1.0.0")

# Allow CORS for local dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@app.get("/api/stats")
def get_stats():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM entities WHERE type='concept'")
        c_cnt = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM entities WHERE type='theorem'")
        t_cnt = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM relationships")
        r_cnt = cur.fetchone()[0]
    return {
        "concepts": c_cnt,
        "theorems": t_cnt,
        "relationships": r_cnt,
        "total": c_cnt + t_cnt
    }

@app.get("/api/graph")
def get_graph(
    filter_type: str = Query("all", description="all, concept, theorem"),
    search: Optional[str] = Query(None, description="search query"),
    limit: int = Query(500, description="max nodes")
):
    with get_db() as conn:
        cur = conn.cursor()
        query = "SELECT id, type, label, statement, restrictions FROM entities"
        params = []
        conditions = []

        if filter_type in ("concept", "theorem"):
            conditions.append("type = ?")
            params.append(filter_type)

        if search and search.strip():
            sq = f"%{search.strip()}%"
            conditions.append("(label LIKE ? OR id LIKE ? OR statement LIKE ?)")
            params.extend([sq, sq, sq])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY label LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()

        node_ids = set()
        nodes = []
        for row in rows:
            node_ids.add(row["id"])
            nodes.append({
                "id": row["id"],
                "label": row["label"] or row["id"],
                "type": row["type"],
                "color": "#B2FFB2" if row["type"] == "concept" else "#FFFF80",
                "statement": row["statement"] or ""
            })

        # Fetch edges directly from SQLite using the composite index idx_rel_source_target
        edges = []
        if node_ids:
            node_ids_list = list(node_ids)
            placeholders = ",".join("?" * len(node_ids_list))
            cur.execute(
                f"""
                SELECT source_id, target_id, rel_type FROM relationships
                WHERE source_id IN ({placeholders})
                  AND target_id IN ({placeholders})
                """,
                node_ids_list + node_ids_list
            )
            for e in cur.fetchall():
                edges.append({
                    "id": f"{e['source_id']}->{e['target_id']}",
                    "source": e["source_id"],
                    "target": e["target_id"],
                    "rel_type": e["rel_type"]
                })

    return {
        "nodes": nodes,
        "edges": edges
    }

@app.get("/api/entities")
def get_entities(
    q: Optional[str] = Query(None, description="Search query"),
    type_filter: str = Query("all", description="all, concept, theorem"),
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    sort_by: str = Query("label", description="label or id")
):
    with get_db() as conn:
        cur = conn.cursor()
        base_where = []
        params = []

        if type_filter in ("concept", "theorem"):
            base_where.append("type = ?")
            params.append(type_filter)

        if q and q.strip():
            sq = f"%{q.strip()}%"
            base_where.append("(label LIKE ? OR id LIKE ? OR statement LIKE ? OR restrictions LIKE ? OR alternate_names LIKE ?)")
            params.extend([sq, sq, sq, sq, sq])

        where_clause = " WHERE " + " AND ".join(base_where) if base_where else ""

        # Count total
        cur.execute(f"SELECT count(*) FROM entities{where_clause}", params)
        total_count = cur.fetchone()[0]

        # Fetch paginated
        order_col = "label" if sort_by == "label" else "id"
        offset = (page - 1) * limit
        cur.execute(
            f"SELECT id, type, label, alternate_names, qualifying_objects, raw_qualifying_objects, restrictions, raw_restrictions, statement, raw_statement, references_text "
            f"FROM entities{where_clause} ORDER BY {order_col} ASC LIMIT ? OFFSET ?",
            params + [limit, offset]
        )
        rows = [dict(r) for r in cur.fetchall()]

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    return {
        "items": rows,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

@app.get("/api/search")
def search_entities(q: str = Query(..., min_length=1), limit: int = Query(10)):
    with get_db() as conn:
        cur = conn.cursor()
        sq = f"%{q.strip()}%"
        cur.execute("""
            SELECT id, type, label, statement FROM entities
            WHERE label LIKE ? OR id LIKE ? OR statement LIKE ?
            ORDER BY
              CASE WHEN label LIKE ? THEN 0 ELSE 1 END,
              label ASC
            LIMIT ?
        """, (sq, sq, sq, f"{q.strip()}%", limit))
        rows = [dict(r) for r in cur.fetchall()]
    return {"items": rows}

@app.get("/api/entity/{entity_id}")
def get_entity_detail(entity_id: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM entities WHERE id = ? OR label = ?", (entity_id, entity_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")

        entity = dict(row)
        entity["raw_rows"] = json.loads(entity["raw_rows"])

        # Fetch outgoing relationships (RelatedConcepts / RelatedTheorems) with their labels & types
        cur.execute("""
            SELECT r.target_id as id, r.target_type as type, r.rel_type, e.label
            FROM relationships r
            LEFT JOIN entities e ON e.id = r.target_id
            WHERE r.source_id = ?
        """, (entity["id"],))
        outgoing = [dict(r) for r in cur.fetchall()]
        for o in outgoing:
            if not o["label"]:
                o["label"] = o["id"]

        # Fetch incoming relationships (what links to this entity)
        cur.execute("""
            SELECT r.source_id as id, r.source_type as type, r.rel_type, e.label
            FROM relationships r
            LEFT JOIN entities e ON e.id = r.source_id
            WHERE r.target_id = ?
        """, (entity["id"],))
        incoming = [dict(r) for r in cur.fetchall()]
        for idx in range(len(incoming)):
            if not incoming[idx]["label"]:
                incoming[idx]["label"] = incoming[idx]["id"]

        entity["outgoing_relationships"] = outgoing
        entity["incoming_relationships"] = incoming

    return entity

# Check if frontend/dist exists, serve static files and SPA fallback
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.api_route("/", methods=["GET", "HEAD"])
    def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
