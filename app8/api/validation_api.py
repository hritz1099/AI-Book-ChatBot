# MCQ, TF, open-answer validation
from chat import validate_mcq_answer,validate_true_false_answer
from fastapi import APIRouter,Body

router=APIRouter(prefix="/validation",tags=["Validation"])

@router.post("/mcq")
def validate_mcq(data:dict=Body(...)):
    validate_response=validate_mcq_answer(
        question_content=data.get("question_content"),
        user_answer=data.get("user_answer")
    )

    return {"validation":validate_response}

@router.post("/true_false")
def validate_generated_true_false(data:dict=Body(...)):
    validate_response=validate_true_false_answer(
        question_content=data.get("question_content"),
        user_answer=data.get("user_answer")
    )

    return {"validation":validate_response}