@ECHO OFF
TITLE BACKEND
CD backend
CALL venv\scripts\activate
uvicorn main:app --reload