#!/bin/bash
# Start backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000 &
# Start admin-spa
cd admin-spa && npm install && npm run dev -- --port 3001 &
# Start mini-app (H5)
cd mini-app && TENANT=scnu node build.config.js && npm run dev:h5 -- --port 3002 &
wait
