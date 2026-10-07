from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from munk.reviewing.models import ReviewKnowledgeHit, ReviewRequest
from munk_knowledge_local import build_excerpt, build_fts_query, merge_ranked_candidates

from .embedding_service import ReviewEmbeddingService
from .knowledge_db import ReviewKnowledgeDb, resolve_runtime_review_db_path
from .sqlite_vec_compat import serialize_float32


@dataclass(frozen=True)
class ReviewRetrievalResult:
    hits: list[ReviewKnowledgeHit]
    debug_payload: dict[str, Any]


class ReviewRetrievalService:
    def __init__(
        self,
        *,
        db: ReviewKnowledgeDb | None = None,
        embedding_service: ReviewEmbeddingService | None = None,
    ) -> None:
        self.db = db or ReviewKnowledgeDb(resolve_runtime_review_db_path(), read_only=True)
        self.embedding_service = embedding_service or ReviewEmbeddingService()

    def retrieve(
        self,
        *,
        request: ReviewRequest,
        query_text: str,
        limit: int = 8,
    ) -> ReviewRetrievalResult:
        explicit_platforms = [str(item) for item in request.platforms]
        inferred_platforms = self._infer_platforms(request.changed_files)
        effective_platforms = explicit_platforms or inferred_platforms
        inferred_domains = self._infer_domains(request.changed_files)
        tags = list(dict.fromkeys(request.tags))
        case_types = [str(item) for item in request.case_types]

        connection = self.db.connect()
        try:
            query_embedding = self.embedding_service.encode_query(query_text)
            filter_rows = self._run_filter_query(
                connection,
                platforms=effective_platforms,
                domains=inferred_domains,
                tags=tags,
                case_types=case_types,
                limit=max(limit * 2, limit),
            )
            fts_rows = self._run_fts_query(
                connection,
                query_text=query_text,
                platforms=effective_platforms,
                domains=inferred_domains,
                tags=tags,
                case_types=case_types,
                limit=max(limit * 2, limit),
            )
            vector_rows = ReviewRetrievalService._run_vector_query(
                connection,
                query_embedding=query_embedding,
                platforms=effective_platforms,
                domains=inferred_domains,
                tags=tags,
                case_types=case_types,
                limit=max(limit * 2, limit),
            )
        finally:
            connection.close()

        merged = self._merge_candidates(
            filter_rows=filter_rows,
            fts_rows=fts_rows,
            vector_rows=vector_rows,
            limit=limit,
        )
        hits = [self._row_to_hit(item) for item in merged]
        debug_payload = {
            "query_text": query_text,
            "explicit_platforms": explicit_platforms,
            "inferred_platforms": inferred_platforms,
            "effective_platforms": effective_platforms,
            "inferred_domains": inferred_domains,
            "tags": tags,
            "case_types": case_types,
            "filter_candidate_count": len(filter_rows),
            "fts_candidate_count": len(fts_rows),
            "vector_candidate_count": len(vector_rows),
            "returned_case_ids": [item["case_id"] for item in merged],
        }
        return ReviewRetrievalResult(hits=hits, debug_payload=debug_payload)

    @staticmethod
    def _run_filter_query(
        connection,  # noqa: ANN001
        *,
        platforms: Sequence[str],
        domains: Sequence[str],
        tags: Sequence[str],
        case_types: Sequence[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        join_tags = bool(tags)
        if platforms:
            placeholders = ", ".join("?" for _ in platforms)
            clauses.append(f"c.platform IN ({placeholders})")
            params.extend(platforms)
        if domains:
            placeholders = ", ".join("?" for _ in domains)
            clauses.append(f"c.domain IN ({placeholders})")
            params.extend(domains)
        if case_types:
            placeholders = ", ".join("?" for _ in case_types)
            clauses.append(f"c.case_type IN ({placeholders})")
            params.extend(case_types)
        if tags:
            placeholders = ", ".join("?" for _ in tags)
            clauses.append(f"t.tag IN ({placeholders})")
            params.extend(tags)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        tag_join_sql = "LEFT JOIN knowledge_case_tags t ON t.case_id = c.case_id" if join_tags else ""
        rows = connection.execute(
            f"""
            SELECT
                c.case_id,
                c.platform,
                c.domain,
                c.topic,
                c.case_type,
                c.title,
                c.summary,
                c.body_md,
                c.source_dir,
                c.body_path,
                c.tags_json,
                c.code_languages_json,
                c.recommended_checks_json,
                1.0 as filter_score
            FROM knowledge_cases c
            {tag_join_sql}
            {where_sql}
            GROUP BY c.case_id
            ORDER BY c.platform, c.domain, c.title
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _run_fts_query(
        connection,  # noqa: ANN001
        *,
        query_text: str,
        platforms: Sequence[str],
        domains: Sequence[str],
        tags: Sequence[str],
        case_types: Sequence[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        trimmed = query_text.strip()
        if not trimmed:
            return []
        fts_query = build_fts_query(trimmed)
        if not fts_query:
            return []
        clauses = ["knowledge_cases_fts MATCH ?"]
        params: list[Any] = [fts_query]
        if platforms:
            placeholders = ", ".join("?" for _ in platforms)
            clauses.append(f"c.platform IN ({placeholders})")
            params.extend(platforms)
        if domains:
            placeholders = ", ".join("?" for _ in domains)
            clauses.append(f"c.domain IN ({placeholders})")
            params.extend(domains)
        if case_types:
            placeholders = ", ".join("?" for _ in case_types)
            clauses.append(f"c.case_type IN ({placeholders})")
            params.extend(case_types)
        join_tags = bool(tags)
        if tags:
            placeholders = ", ".join("?" for _ in tags)
            clauses.append(f"t.tag IN ({placeholders})")
            params.extend(tags)
        where_sql = " AND ".join(clauses)
        tag_join_sql = "LEFT JOIN knowledge_case_tags t ON t.case_id = c.case_id" if join_tags else ""
        rows = connection.execute(
            f"""
            SELECT
                c.case_id,
                c.platform,
                c.domain,
                c.topic,
                c.case_type,
                c.title,
                c.summary,
                c.body_md,
                c.source_dir,
                c.body_path,
                c.tags_json,
                c.code_languages_json,
                c.recommended_checks_json,
                bm25(knowledge_cases_fts) * -1.0 AS fts_score
            FROM knowledge_cases_fts f
            JOIN knowledge_cases c ON c.case_id = f.case_id
            {tag_join_sql}
            WHERE {where_sql}
            ORDER BY fts_score DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _run_vector_query(
        connection,  # noqa: ANN001
        *,
        query_embedding,
        platforms: Sequence[str],
        domains: Sequence[str],
        tags: Sequence[str],
        case_types: Sequence[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        clauses = ["embedding MATCH ?", "k = ?"]
        serialized_query = serialize_float32(query_embedding)
        params = [serialized_query, limit]
        if platforms:
            placeholders = ", ".join("?" for _ in platforms)
            clauses.append(f"platform IN ({placeholders})")
            params.extend(platforms)
        if domains:
            placeholders = ", ".join("?" for _ in domains)
            clauses.append(f"domain IN ({placeholders})")
            params.extend(domains)
        if case_types:
            placeholders = ", ".join("?" for _ in case_types)
            clauses.append(f"case_type IN ({placeholders})")
            params.extend(case_types)
        outer_clauses: list[str] = []
        outer_params: list[Any] = []
        tag_join_sql = ""
        if tags:
            tag_join_sql = "LEFT JOIN knowledge_case_tags t ON t.case_id = c.case_id"
            placeholders = ", ".join("?" for _ in tags)
            outer_clauses.append(f"t.tag IN ({placeholders})")
            outer_params.extend(tags)
        outer_where = f"WHERE {' AND '.join(outer_clauses)}" if outer_clauses else ""
        rows = connection.execute(
            f"""
            WITH vector_hits AS (
                SELECT
                    case_rowid,
                    distance
                FROM knowledge_case_embeddings
                WHERE {' AND '.join(clauses)}
                ORDER BY distance
            )
            SELECT
                c.case_id,
                c.platform,
                c.domain,
                c.topic,
                c.case_type,
                c.title,
                c.summary,
                c.body_md,
                c.source_dir,
                c.body_path,
                c.tags_json,
                c.code_languages_json,
                c.recommended_checks_json,
                vector_hits.distance AS vector_distance
            FROM vector_hits
            JOIN knowledge_cases c ON c.rowid = vector_hits.case_rowid
            {tag_join_sql}
            {outer_where}
            GROUP BY c.case_id
            ORDER BY vector_hits.distance ASC
            LIMIT ?
            """,
            tuple([*params, *outer_params, limit]),
        ).fetchall()
        return [dict(row) for row in rows]

    def _merge_candidates(
        self,
        *,
        filter_rows: list[dict[str, Any]],
        fts_rows: list[dict[str, Any]],
        vector_rows: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        return merge_ranked_candidates(
            filter_rows=filter_rows,
            fts_rows=fts_rows,
            vector_rows=vector_rows,
            id_field="case_id",
            limit=limit,
        )

    @staticmethod
    def _row_to_hit(row: dict[str, Any]) -> ReviewKnowledgeHit:
        import json

        body_path = Path(row["body_path"])
        body_md = str(row.get("body_md", "") or "")
        excerpt = build_excerpt(body_md)
        return ReviewKnowledgeHit(
            case_id=row["case_id"],
            platform=row["platform"],
            domain=row["domain"],
            topic=row["topic"],
            case_type=row["case_type"],
            title=row["title"],
            summary=row["summary"],
            tags=json.loads(row["tags_json"]),
            recommended_checks=json.loads(row["recommended_checks_json"]),
            code_languages=json.loads(row["code_languages_json"]),
            source_dir=Path(row["source_dir"]),
            body_path=body_path,
            body_excerpt=excerpt,
            retrieval_channels=list(dict.fromkeys(row.get("retrieval_channels", []))),
            vector_distance=row.get("vector_distance"),
            fts_score=row.get("fts_score"),
            filter_score=row.get("filter_score"),
            combined_score=row.get("combined_score"),
        )

    @staticmethod
    def _infer_platforms(changed_files: list[str]) -> list[str]:
        lowered = [item.lower() for item in changed_files]
        inferred: list[str] = []
        if any(
            marker in item
            for item in lowered
            for marker in (".kt", ".kts", "androidmanifest.xml", "build.gradle", "gradle")
        ):
            inferred.append("android")
        if any(
            marker in item
            for item in lowered
            for marker in (".swift", ".m", ".mm", ".xcodeproj", ".pbxproj", ".plist")
        ):
            inferred.append("ios")
        if any(
            marker in item
            for item in lowered
            for marker in (".ts", ".tsx", ".js", ".jsx", ".vue", ".css", ".scss", "package.json")
        ):
            inferred.append("web")
        return list(dict.fromkeys(inferred))

    @staticmethod
    def _infer_domains(changed_files: list[str]) -> list[str]:
        lowered = " ".join(item.lower() for item in changed_files)
        domains: list[str] = []
        if any(token in lowered for token in ("fragment", "viewbinding", "ime", "customview", "view/")):
            domains.append("ui-view-system")
        if any(token in lowered for token in ("compose", "composable", "remember", "navhost")):
            domains.append("ui-jetpack-compose")
        if any(token in lowered for token in ("activity", "fragment", "uikit", "swiftui", "appdelegate", "scene")):
            domains.append("platform-framework")
        if any(token in lowered for token in ("react", ".tsx", ".jsx")):
            domains.append("framework-react")
        if any(token in lowered for token in ("vue", ".vue", "pinia")):
            domains.append("framework-vue")
        if any(token in lowered for token in ("kotlin", ".kt", ".kts")):
            domains.append("language-kotlin")
        if any(token in lowered for token in ("swift", ".swift")):
            domains.append("language-swift")
        if any(token in lowered for token in ("swiftui", "viewmodifier", "@state", "@observedobject")):
            domains.append("ui-swiftui")
        if any(token in lowered for token in ("uikit", "uiview", "uiviewcontroller", "uitableview", "uicollectionview")):
            domains.append("ui-uikit")
        if any(token in lowered for token in ("coredata", "userdefaults", "cache", "sqlite", "persistence")):
            domains.append("data-persistence")
        if any(token in lowered for token in ("async", "await", "actor", "task", "stream")):
            domains.append("concurrency-swift")
        if any(token in lowered for token in ("window", "document", "history", "cookie", "storage", "clipboard")):
            domains.append("browser-platform")
        if any(token in lowered for token in ("csrf", "xss", "auth", "token", "cookie")):
            domains.append("security-privacy")
        if any(token in lowered for token in ("store", "reducer", "mobx", "redux", "pinia", "zustand")):
            domains.append("architecture-state-management")
        if "network" in lowered or "api" in lowered:
            domains.append("network")
        if "state" in lowered or "store" in lowered:
            domains.append("state")
        return list(dict.fromkeys(domains))
