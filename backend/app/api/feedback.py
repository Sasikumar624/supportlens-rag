from fastapi import APIRouter, Depends, status

from app.api.dependencies import feedback_store
from app.api.schemas import FeedbackRequest, FeedbackResponse


router = APIRouter(prefix="/api")


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
