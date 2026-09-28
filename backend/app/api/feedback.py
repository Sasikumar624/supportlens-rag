from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.api.dependencies import feedback_store


router = APIRouter(prefix="/api")


class FeedbackRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class FeedbackResponse(BaseModel):
    feedback_id: int
    status: str


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    payload: FeedbackRequest,
    feedback_items: list[dict] = Depends(feedback_store),
) -> FeedbackResponse:
    feedback_id = len(feedback_items) + 1
    feedback_items.append(
        {
            "feedback_id": feedback_id,
            "question": payload.question,
            "answer": payload.answer,
            "rating": payload.rating,
            "comment": payload.comment,
        }
    )
    return FeedbackResponse(feedback_id=feedback_id, status="stored")
