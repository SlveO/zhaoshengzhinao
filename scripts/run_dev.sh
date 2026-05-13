#!/bin/bash
# Start backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000 &
# Start frontend
cd frontend && npm install && npm run dev
