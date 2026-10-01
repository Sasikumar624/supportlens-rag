from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.rag.generator import NoAnswerConfig, PromptConfig, RAGPipeline
from app.rag.hybrid_retriever import HybridRetrievalConfig, HybridRetriever
from app.rag.keyword_retriever import QdrantKeywordRetriever
from app.rag.local_llm import LazyLocalHuggingFaceLLMClient
from app.rag.query_processing import QueryProcessingRetriever
from app.rag.reranker import CrossEncoderReranker, RerankedRetriever, RerankingConfig
from app.rag.retriever import DenseRetriever


SUPPORTED_LLM_PROVIDERS = {"local"}


@dataclass(frozen=True)
class RuntimePipelineConfig:
    llm_provider: str

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "RuntimePipelineConfig":
        settings = settings or get_settings()
        return cls(llm_provider=settings.llm_provider)

    def validate(self) -> None:
        if self.llm_provider not in SUPPORTED_LLM_PROVIDERS:
            supported = ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
            raise RuntimeError(
                f"Unsupported LLM_PROVIDER={self.llm_provider!r}. "
                f"Supported providers: {supported}."
            )


def build_query_pipeline_from_settings(
    settings: Settings | None = None,
) -> RAGPipeline:
    settings = settings or get_settings()
    RuntimePipelineConfig.from_settings(settings).validate()

    reranking_config = RerankingConfig.from_settings()
    keyword_retriever = QdrantKeywordRetriever.from_settings()
    if settings.dense_retrieval_enabled:
        dense_retriever = DenseRetriever.from_settings(
            top_k=reranking_config.candidate_top_k
        )
        hybrid_retriever = HybridRetriever(
            dense_retriever=dense_retriever,
            keyword_retriever=keyword_retriever,
            config=HybridRetrievalConfig(
                top_k=reranking_config.candidate_top_k
                if settings.reranking_enabled
                else reranking_config.final_top_k,
                rrf_k=settings.hybrid_rrf_k,
            ),
        )
        base_retriever = (
            RerankedRetriever(
                retriever=hybrid_retriever,
                reranker=CrossEncoderReranker.from_settings(),
                config=reranking_config,
            )
            if settings.reranking_enabled
            else hybrid_retriever
        )
    else:
        base_retriever = keyword_retriever
    retriever = QueryProcessingRetriever(base_retriever)
    llm_client = (
        LazyLocalHuggingFaceLLMClient.from_settings()
        if settings.llm_generation_enabled
        else None
    )

    return RAGPipeline(
        retriever=retriever,
        llm_client=llm_client,
        prompt_config=PromptConfig.from_settings(),
        no_answer_config=NoAnswerConfig.from_settings(),
    )
