import re
from dataclasses import dataclass, field
from typing import Protocol

from app.rag.retriever import MetadataFilter, RetrievalResult


ERROR_CODE_PATTERN = re.compile(r"\b[A-Z]{2,}_[A-Z0-9_]+\b", re.IGNORECASE)
FIRMWARE_PATTERN = re.compile(r"\b(?:FW|FIRMWARE)[_-]?\d+(?:\.\d+)+(?:[-_][A-Z0-9]+)?\b", re.IGNORECASE)
IP_ADDRESS_PATTERN = re.compile(
    r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b"
)
MODEL_PATTERN = re.compile(r"\b[A-Z]{1,5}\d{2,}[A-Z0-9_-]*\b", re.IGNORECASE)

DEFAULT_CATEGORY_ALIASES = {
    "setup": (
        "setup",
        "set up",
        "install",
        "installing",
        "installation",
        "quick start",
        "first steps",
        "getting started",
        "guide me",
    ),
    "troubleshooting": (
        "troubleshoot",
        "troubleshooting",
        "not working",
        "no internet",
        "connectivity",
        "reset",
        "recover",
        "failsafe",
    ),
    "configuration": ("configure", "configuration", "wi-fi", "wifi", "wireless"),
    "firmware": ("firmware", "upgrade", "sysupgrade", "luci"),
    "faq": (
        "what is",
        "what are",
        "define",
        "definition",
        "overview",
        "explain",
        "tell me about",
    ),
}

DEFAULT_PRODUCT_ALIASES = {
    "TP-Link Archer AX21": ("archer ax21", "ax21"),
    "TP-Link Archer AX55": ("archer ax55", "ax55"),
    "TP-Link Routers": ("tp-link", "tplink", "tp link", "archer"),
    "NETGEAR Routers": ("netgear", "nighthawk", "routerlogin"),
    "ASUS Routers": ("asus", "asuswrt", "asus router", "asusrouter"),
}


class Retriever(Protocol):
    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        ...


@dataclass(frozen=True)
class QueryProcessingConfig:
    known_products: tuple[str, ...] = (
        "OpenWrt",
        "TP-Link Archer AX21",
        "TP-Link Archer AX55",
        "TP-Link Routers",
        "NETGEAR Routers",
        "ASUS Routers",
    )
    known_versions: tuple[str, ...] = ("current",)
    category_aliases: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: dict(DEFAULT_CATEGORY_ALIASES)
    )
    product_aliases: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: dict(DEFAULT_PRODUCT_ALIASES)
    )

    def __post_init__(self) -> None:
        if any(not product.strip() for product in self.known_products):
            raise ValueError("known_products cannot contain empty values")
        if any(not version.strip() for version in self.known_versions):
            raise ValueError("known_versions cannot contain empty values")
        for category, aliases in self.category_aliases.items():
            if not category.strip():
                raise ValueError("category aliases cannot contain empty categories")
            if any(not alias.strip() for alias in aliases):
                raise ValueError("category aliases cannot contain empty aliases")
        for product, aliases in self.product_aliases.items():
            if not product.strip():
                raise ValueError("product aliases cannot contain empty products")
            if any(not alias.strip() for alias in aliases):
                raise ValueError("product alias lists cannot contain empty aliases")


@dataclass(frozen=True)
class QueryIdentifiers:
    error_codes: list[str]
    firmware_versions: list[str]
    model_numbers: list[str]
    ip_addresses: list[str]

    @property
    def all(self) -> list[str]:
        return _unique_preserve_order(
            [
                *self.error_codes,
                *self.firmware_versions,
                *self.model_numbers,
                *self.ip_addresses,
            ]
        )


@dataclass(frozen=True)
class ProcessedQuery:
    original_query: str
    normalized_query: str
    identifiers: QueryIdentifiers
    detected_product: str | None = None
    detected_version: str | None = None
    detected_category: str | None = None

    @property
    def metadata_filter(self) -> MetadataFilter | None:
        if not any(
            [self.detected_product, self.detected_version, self.detected_category]
        ):
            return None
        return MetadataFilter(
            product=self.detected_product,
            version=self.detected_version,
            category=self.detected_category,
        )


class QueryProcessor:
    def __init__(self, config: QueryProcessingConfig | None = None) -> None:
        self.config = config or QueryProcessingConfig()

    def process(self, query: str) -> ProcessedQuery:
        normalized_query = normalize_query(query)
        if not normalized_query:
            raise ValueError("query cannot be empty")

        return ProcessedQuery(
            original_query=query,
            normalized_query=normalized_query,
            identifiers=detect_identifiers(normalized_query),
            detected_product=_detect_product(
                normalized_query,
                self.config.known_products,
                self.config.product_aliases,
            ),
            detected_version=_detect_known_value(
                normalized_query,
                self.config.known_versions,
            ),
            detected_category=_detect_category(
                normalized_query,
                self.config.category_aliases,
            ),
        )


class QueryProcessingRetriever:
    def __init__(
        self,
        retriever: Retriever,
        processor: QueryProcessor | None = None,
    ) -> None:
        self._retriever = retriever
        self._processor = processor or QueryProcessor()
        self.last_processed_query: ProcessedQuery | None = None

    def retrieve(
        self,
        query: str,
        *,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievalResult]:
        processed_query = self._processor.process(query)
        self.last_processed_query = processed_query
        effective_filter = merge_metadata_filters(
            explicit_filter=metadata_filter,
            inferred_filter=processed_query.metadata_filter,
        )
        return self._retriever.retrieve(
            processed_query.normalized_query,
            metadata_filter=effective_filter,
        )


def normalize_query(query: str) -> str:
    return " ".join(query.strip().split())


def detect_identifiers(query: str) -> QueryIdentifiers:
    firmware_versions = _unique_matches(FIRMWARE_PATTERN, query)
    error_codes = [
        value
        for value in _unique_matches(ERROR_CODE_PATTERN, query)
        if not any(
            firmware.lower().startswith(value.lower())
            for firmware in firmware_versions
        )
    ]
    ip_addresses = _unique_matches(IP_ADDRESS_PATTERN, query)
    model_numbers = [
        value
        for value in _unique_matches(MODEL_PATTERN, query)
        if value not in error_codes and value not in firmware_versions
    ]
    return QueryIdentifiers(
        error_codes=error_codes,
        firmware_versions=firmware_versions,
        model_numbers=model_numbers,
        ip_addresses=ip_addresses,
    )


def merge_metadata_filters(
    *,
    explicit_filter: MetadataFilter | None,
    inferred_filter: MetadataFilter | None,
) -> MetadataFilter | None:
    if explicit_filter is None:
        return inferred_filter
    if inferred_filter is None:
        return explicit_filter

    return MetadataFilter(
        product=explicit_filter.product or inferred_filter.product,
        version=explicit_filter.version or inferred_filter.version,
        category=explicit_filter.category or inferred_filter.category,
        language=explicit_filter.language or inferred_filter.language,
        source_type=explicit_filter.source_type or inferred_filter.source_type,
        document_id=explicit_filter.document_id or inferred_filter.document_id,
    )


def _detect_known_value(query: str, known_values: tuple[str, ...]) -> str | None:
    query_lower = query.lower()
    for value in known_values:
        if re.search(rf"(?<!\w){re.escape(value.lower())}(?!\w)", query_lower):
            return value
    return None


def _detect_product(
    query: str,
    known_products: tuple[str, ...],
    product_aliases: dict[str, tuple[str, ...]],
) -> str | None:
    exact_match = _detect_known_value(query, known_products)
    if exact_match is not None:
        return exact_match

    query_lower = query.lower()
    for product in known_products:
        for alias in product_aliases.get(product, ()):
            if re.search(rf"(?<!\w){re.escape(alias.lower())}(?!\w)", query_lower):
                return product
    return None


def _detect_category(
    query: str,
    category_aliases: dict[str, tuple[str, ...]],
) -> str | None:
    query_lower = query.lower()
    for category, aliases in category_aliases.items():
        for alias in aliases:
            if alias.lower() in query_lower:
                return category
    return None


def _unique_matches(pattern: re.Pattern, query: str) -> list[str]:
    return _unique_preserve_order(match.group(0) for match in pattern.finditer(query))


def _unique_preserve_order(values) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_values.append(value)
    return unique_values
