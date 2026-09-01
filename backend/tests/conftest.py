import os
import re
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def test_credentials():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing credentials file")
    c = p.read_text(encoding="utf-8")
    em = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    pw = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?password(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    if not em or not pw:
        pytest.skip("no creds found")
    return {"email": em.group(1), "password": pw.group(1)}


@pytest.fixture(scope="session")
def demo_client(test_credentials):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=test_credentials, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:400]}")
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"no token in {r.json()}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="session")
def other_client():
    """A second freshly-created onboarded user (for auth isolation)."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"TEST_qa_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/signup", json={"email": email, "password": "Test1234!", "name": "TEST QA"}, timeout=60)
    if r.status_code not in (200, 201):
        pytest.fail(f"signup failed {r.status_code}: {r.text[:400]}")
    tok = r.json().get("token") or r.json().get("access_token")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    s.post(f"{API}/auth/onboarding", json={
        "name": "TEST QA", "university": "TEST U", "degree_course": "TEST C",
        "daily_hours": 3, "available_days": ["lun", "mar", "mer", "gio", "ven"],
    }, timeout=60)
    return s
