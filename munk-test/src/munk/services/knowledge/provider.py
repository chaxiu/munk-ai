from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from munk.app_knowledge import (
    AppKnowledgeImportDocument,
    AppKnowledgeRuntime,
    KnowledgeCard,
    KnowledgeCardType,
    KnowledgeGetRequest,
    KnowledgeListRequest,
    KnowledgeSearchRequest,
    KnowledgeSubmitCandidateRequest,
    create_knowledge_runtime,
)
from munk.app_knowledge.repository import ImportedKnowledgeRepository
from munk.knowledge import KnowledgeManagedPaths, KnowledgeRuntimeContext
from munk.shared_tools import KnowledgeToolProvider


@dataclass(frozen=True)
class ImportedKnowledgeProvider(KnowledgeToolProvider):
    expected_app_id: str
    repository: ImportedKnowledgeRepository

    def search(
        self,
        query: str,
        *,
        card_types: Sequence[KnowledgeCardType] | None = None,
        limit: int = 8,
    ) -> list[KnowledgeCard]:
        selected_types = list(card_types) if card_types is not None else None
        return self.repository.search_cards(
            self.expected_app_id,
            query,
            card_types=selected_types,
            limit=limit,
        )

    def get(self, card_id: str) -> KnowledgeCard | None:
        card = self.repository.get_card(card_id)
        if card is None or card.app_id != self.expected_app_id:
            return None
        return card

    def list(
        self,
        *,
        card_type: KnowledgeCardType | None = None,
        limit: int = 20,
    ) -> list[KnowledgeCard]:
        return self.repository.list_cards(self.expected_app_id, card_type=card_type, limit=limit)

    def submit_candidate(self, submission):  # noqa: ANN001, ANN201
        del submission
        raise NotImplementedError("knowledge candidate submission is out of scope for the read-layer phase")


def build_knowledge_provider_from_document(
    document: AppKnowledgeImportDocument,
) -> ImportedKnowledgeProvider:
    repository = ImportedKnowledgeRepository(document=document)
    return ImportedKnowledgeProvider(expected_app_id=document.app_id, repository=repository)


@dataclass(frozen=True)
class RuntimeBackedKnowledgeProvider(KnowledgeToolProvider):
    expected_app_id: str
    runtime: AppKnowledgeRuntime
    runtime_context: KnowledgeRuntimeContext

    def search(
        self,
        query: str,
        *,
        card_types: Sequence[KnowledgeCardType] | None = None,
        limit: int = 8,
    ) -> list[KnowledgeCard]:
        output = self.runtime.search(
            KnowledgeSearchRequest(
                app_id=self.expected_app_id,
                query=query,
                card_types=list(card_types or []),
                limit=limit,
            ),
            context=self.runtime_context,
        )
        return list(output.items)

    def get(self, card_id: str) -> KnowledgeCard | None:
        output = self.runtime.get(
            KnowledgeGetRequest(app_id=self.expected_app_id, card_id=card_id),
            context=self.runtime_context,
        )
        if output.card is None or output.card.app_id != self.expected_app_id:
            return None
        return output.card

    def list(
        self,
        *,
        card_type: KnowledgeCardType | None = None,
        limit: int = 20,
    ) -> list[KnowledgeCard]:
        output = self.runtime.list(
            KnowledgeListRequest(
                app_id=self.expected_app_id,
                card_type=card_type,
                limit=limit,
            ),
            context=self.runtime_context,
        )
        return list(output.items)

    def submit_candidate(self, submission):
        output = self.runtime.submit_candidate(
            KnowledgeSubmitCandidateRequest(submission=submission),
            context=self.runtime_context,
        )
        if output.candidate is None:
            raise RuntimeError("knowledge runtime returned no candidate record")
        return output.candidate


def build_runtime_backed_knowledge_provider(
    *,
    app_id: str,
    assets_root: Path,
    resolved_config: object | None = None,
) -> RuntimeBackedKnowledgeProvider:
    runtime = create_knowledge_runtime(resolved_config=resolved_config or {"app_registry_root": assets_root})
    runtime_context = KnowledgeRuntimeContext(
        operation_id=None,
        managed_paths=KnowledgeManagedPaths(root_dir=assets_root),
    )
    return RuntimeBackedKnowledgeProvider(
        expected_app_id=app_id,
        runtime=runtime,
        runtime_context=runtime_context,
    )
