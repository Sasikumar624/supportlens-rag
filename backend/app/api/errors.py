from enum import StrEnum

from fastapi import HTTPException, status


class ApiErrorCode(StrEnum):
    REQUEST_TOO_LARGE = "request_too_large"
    EMPTY_QUESTION = "empty_question"
    QUESTION_TOO_LONG = "question_too_long"
    INVALID_METADATA = "invalid_metadata"
    QUERY_PIPELINE_UNAVAILABLE = "query_pipeline_unavailable"
    QUERY_PIPELINE_FAILED = "query_pipeline_failed"
    DUPLICATE_DOCUMENT = "duplicate_document"
    DOCUMENT_NOT_FOUND = "document_not_found"
    DOCUMENT_INGESTION_NOT_CONFIGURED = "document_ingestion_not_configured"
    DOCUMENT_DELETION_NOT_CONFIGURED = "document_deletion_not_configured"


def api_error(
    *,
    status_code: int,
    code: ApiErrorCode,
    message: str,
    field: str | None = None,
) -> HTTPException:
    detail = {
        "code": code.value,
        "message": message,
    }
    if field is not None:
        detail["field"] = field
    return HTTPException(status_code=status_code, detail=detail)


def bad_request(
    code: ApiErrorCode,
    message: str,
    *,
    field: str | None = None,
) -> HTTPException:
    return api_error(
        status_code=status.HTTP_400_BAD_REQUEST,
        code=code,
        message=message,
        field=field,
    )


def conflict(
    code: ApiErrorCode,
    message: str,
    *,
    field: str | None = None,
) -> HTTPException:
    return api_error(
        status_code=status.HTTP_409_CONFLICT,
        code=code,
        message=message,
        field=field,
    )


def not_found(
    code: ApiErrorCode,
    message: str,
    *,
    field: str | None = None,
) -> HTTPException:
    return api_error(
        status_code=status.HTTP_404_NOT_FOUND,
        code=code,
        message=message,
        field=field,
    )


def service_unavailable(
    code: ApiErrorCode,
    message: str,
) -> HTTPException:
    return api_error(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code=code,
        message=message,
    )
