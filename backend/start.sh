#!/bin/bash
echo "Starting VeritasAI Backend..."
cd backend
pip install -r requirements.txt
python -c "from rag.vector_store import build_index; build_index()"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
