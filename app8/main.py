from fastapi import FastAPI
from api.chat_api import router as chat_router
from api.validation_api import router as validation_router
from api.question import router as question_router
from api.assessment_api import router as assessment_router

app=FastAPI(title="Book Chatbot API")
app.include_router(validation_router)
app.include_router(question_router)
app.include_router(assessment_router)
app.include_router(chat_router)

@app.get("/")
def check():
    return {
        "status": "API running"
    }