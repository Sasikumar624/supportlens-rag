from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.rag.generator import NoAnswerConfig, RAGPipeline
from app.rag.local_llm import LocalHuggingFaceLLMClient
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
    dense_retriever = DenseRetriever.from_settings(top_k=reranking_config.candidate_top_k)
    reranked_retriever = RerankedRetriever(
        retriever=dense_retriever,
        reranker=CrossEncoderReranker.from_settings(),
        config=reranking_config,
    )
    retriever = QueryProcessingRetriever(reranked_retriever)
    llm_client = LocalHuggingFaceLLMClient.from_settings()

    return RAGPipeline(
        retriever=retriever,
        llm_client=llm_client,
        no_answer_config=NoAnswerConfig.from_settings(),
    )
