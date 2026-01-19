# question generation APIs
#question_api.py,generate question,follow-up questions
from chat import generate_question_with_type,generate_question_from_chunk
from fastapi import APIRouter,Body

router=APIRouter(prefix="/questions",tags=["Questions"])

@router.get("/generate")
def generate_question_type(data:dict=Body(...)):
    question=generate_question_with_type(
    chunk_text=data.get("chunk_text"),
    question_type=data.get("question_type","open"),
    difficulty=data.get("difficulty","intermediate")
    # prev_question=data.get("prev_question"),
    # prev_answer=data.get("prev_answer")
    )
    return {"question":question}


# @router.post("/generate-question_type")
# def generate_question_type(data:dict=Body(...)):
#     question=generate_question_with_type(
#     chunk_text=data.get("chunk_text"),
#     question_type=data.get("question_type","open"),
#     difficulty=data.get("difficulty","intermediate"),
#     prev_question=data.get("prev_question"),
#     prev_answer=data.get("prev_answer")
#     )
#     return {"question":question}


# @router.post("/generate-question")
# def generate_question_api(data:dict=Body(...)):
#     question=generate_question_from_chunk(
#        chunk_text=data.get("chunk_text"),
#        prev_question=data.get("prev_question"),
#        prev_answer=data.get("prev_answer"),
#        difficulty=data.get("difficulty","intermediate")
#     )
#     return {"question": question}
