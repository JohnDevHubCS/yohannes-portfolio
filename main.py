"""
Contact API for the portfolio.
Run:  uvicorn main:app --reload --port 8000
Env:  ALLOWED_ORIGINS  comma-separated site origins (CORS)
      CONTACT_TO       where messages are emailed (default: johnelves887@gmail.com)
      SMTP_USER / SMTP_PASS  Gmail address + App Password (never put these in code)
"""
import os
import re
import smtplib
import sqlite3
import time
from collections import defaultdict, deque
from email.message import EmailMessage

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

ALLOWED = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",") if o.strip()]
TO = os.getenv("CONTACT_TO", "johnelves887@gmail.com")
SMTP_USER, SMTP_PASS = os.getenv("SMTP_USER"), os.getenv("SMTP_PASS")
DB = os.getenv("DB_PATH", "messages.db")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_PER_HOUR = 5
hits: dict[str, deque] = defaultdict(deque)

app = FastAPI(title="Portfolio contact API", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED,
                   allow_methods=["POST"], allow_headers=["Content-Type"])


class Contact(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    email: str = Field(default="", max_length=120)
    message: str = Field(min_length=10, max_length=1500)
    website: str = ""  # honeypot: real visitors leave this empty

    @field_validator("name", "email", "message")
    @classmethod
    def clean(cls, v: str) -> str:
        return re.sub(r"[\x00-\x08\x0b-\x1f]", "", v).strip()

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        if v and not EMAIL_RE.match(v):
            raise ValueError("invalid email")
        return v


def save(data: Contact, ip: str) -> None:
    with sqlite3.connect(DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS messages("
                  "id INTEGER PRIMARY KEY, ts REAL, ip TEXT, name TEXT, email TEXT, message TEXT)")
        c.execute("INSERT INTO messages(ts,ip,name,email,message) VALUES (?,?,?,?,?)",
                  (time.time(), ip, data.name, data.email, data.message))  # parameterised: no SQL injection


def send_mail(data: Contact) -> None:
    if not (SMTP_USER and SMTP_PASS):
        return  # still saved in the database
    msg = EmailMessage()
    msg["Subject"] = "Portfolio message from " + data.name.replace("\n", " ")
    msg["From"], msg["To"] = SMTP_USER, TO
    if data.email:
        msg["Reply-To"] = data.email
    msg.set_content(f"Name: {data.name}\nEmail: {data.email or '-'}\n\n{data.message}")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
    except Exception as exc:  # do not leak details to the visitor
        print("mail error:", type(exc).__name__)


@app.post("/contact")
def contact(data: Contact, request: Request, bg: BackgroundTasks):
    ip = request.client.host if request.client else "unknown"
    now, q = time.time(), hits[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= MAX_PER_HOUR:
        raise HTTPException(429, "Too many messages. Please try again later.")
    q.append(now)
    if data.website:  # bot filled the honeypot: pretend success, store nothing
        return {"ok": True}
    save(data, ip)
    bg.add_task(send_mail, data)
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok"}
