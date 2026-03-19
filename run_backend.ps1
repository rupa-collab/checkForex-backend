param(
    [int]$Port = 8000
)

if (!(Test-Path .venv)) {
    python -m venv .venv
}

.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port $Port
