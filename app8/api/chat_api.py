# /api/chat, /api/greeting-chat_api.py
#greeting,chat response,classify response

from chat import get_chat_response,generate_greeting_message
from fastapi import APIRouter

router=APIRouter()
@router.post("/chat")
def chat_api(message:list[dict],model:str="llama3.2:latest"):
    response=get_chat_response(message,model)
    return {"response":response}

@router.get("/greeting")
def greeting_api(username:str="Guest"):
    message=generate_greeting_message(username)
    return {"message":message}