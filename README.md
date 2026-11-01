# Portfolio contact backend (FastAPI)

1. `cd backend && pip install -r requirements.txt`
2. Set environment variables (Windows PowerShell example):
   `$env:SMTP_USER="you@gmail.com"; $env:SMTP_PASS="gmail-app-password"; $env:ALLOWED_ORIGINS="http://127.0.0.1:5500"`
   (Create a Gmail App Password in your Google account security settings.)
3. `uvicorn main:app --reload --port 8000`
4. In `index.html` set `const API_URL="http://127.0.0.1:8000/contact";`

For production, deploy to Render, Railway or Fly.io, set `ALLOWED_ORIGINS` to your real site
(for example `https://yohannes.dev`) and use the deployed URL as `API_URL`.
Messages are also stored in `messages.db`. Features: validation, honeypot, 5 messages/hour per IP,
strict CORS, parameterised SQL, secrets only from environment variables.
