"""Load test. Run against a live instance:

    locust -f tests/locustfile.py --host http://localhost:8000
"""
from __future__ import annotations

from locust import HttpUser, between, task


class ChatUser(HttpUser):
    wait_time = between(1, 4)
    token: str | None = None

    def on_start(self) -> None:
        # Assumes the seed tenant exists (scripts/seed.py).
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@demo.test", "password": "demo12345", "tenant_slug": "demo"},
        )
        if resp.status_code == 200:
            self.token = resp.json()["access_token"]

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def list_sessions(self) -> None:
        self.client.get("/api/v1/chat/sessions", headers=self.headers)

    @task(1)
    def search(self) -> None:
        self.client.post(
            "/api/v1/search/documents",
            headers=self.headers,
            json={"query": "refund policy", "mode": "hybrid", "top_k": 5},
        )

    @task(1)
    def health(self) -> None:
        self.client.get("/api/v1/health")
