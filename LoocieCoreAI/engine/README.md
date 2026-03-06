# LoocieCoreAI Core Engine (Build/Test)

Quick start:
1) python3 -m venv .venv
2) source .venv/bin/activate
3) pip install -r requirements.txt
4) cp .env.example .env
5) edit .env and set LOOCIE_INTERNAL_KEY
6) uvicorn app.main:app --host 127.0.0.1 --port 8080
