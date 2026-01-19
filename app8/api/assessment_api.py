# report API
from chat import generate_assessment_report,evaluate_open_answer
from fastapi import APIRouter,Body

router=APIRouter(prefix="/report",tags=["Reports"])

@router.post("/assessment-report")
def report_generation(data:dict=Body(...)):
    assessment_report=generate_assessment_report(
        assessment_results=data.get("assessment_results"),
        overall_percentage=data.get("overall_percentage"),
        difficulty=data.get("difficulty")
    )

    return {"report":assessment_report}

@router.post("/evaluate-open")
def evaluate_open(data: dict = Body(...)):
    feedback, score = evaluate_open_answer(
        question=data["question"],
        user_answer=data["user_answer"],
        context=data["context"],
        difficulty=data.get("difficulty", "intermediate")
    )

    return {
        "feedback": feedback,
        "score": score
    }