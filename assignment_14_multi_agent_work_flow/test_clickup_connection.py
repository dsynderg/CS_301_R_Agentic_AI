import os
import unittest
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


DEFAULT_CLICKUP_BASE = "https://api.clickup.com/api/v2"
TARGET_LIST_ID = "901707482100"


def _normalize_clickup_base_url(raw_url: str | None) -> str:
    if not raw_url:
        return DEFAULT_CLICKUP_BASE

    url = raw_url.strip().rstrip("/")

    # ClickUp API host should be api.clickup.com; fix common app.clickup.com mistake.
    if "app.clickup.com" in url:
        url = url.replace("app.clickup.com", "api.clickup.com")

    # Most ClickUp REST endpoints are under /api/v2.
    if url.endswith("/api"):
        url = f"{url}/v2"
    elif "/api/v2" not in url:
        url = f"{url}/api/v2"

    return url


class ClickUpConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv()
        cls.token = os.getenv("CLICKUP_API_TOKEN", "").strip()
        cls.raw_url = os.getenv("CLICKUP_API_URL", "").strip()
        cls.base_url = _normalize_clickup_base_url(cls.raw_url)

    def _auth_headers(self):
        return {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }

    def test_clickup_token_present(self):
        self.assertTrue(
            self.token,
            "CLICKUP_API_TOKEN is missing or empty in .env",
        )

    def test_clickup_base_url_is_valid(self):
        parsed = urlparse(self.base_url)
        self.assertIn(parsed.scheme, {"http", "https"}, "CLICKUP_API_URL must be an http/https URL")
        self.assertTrue(parsed.netloc, "CLICKUP_API_URL is missing a host")

    def test_clickup_server_reachable(self):
        # This checks DNS + TLS + basic HTTP reachability for the ClickUp API host.
        response = requests.get(self.base_url, timeout=15)
        self.assertLess(
            response.status_code,
            500,
            f"ClickUp host reachable but returned server error {response.status_code}",
        )

    def test_clickup_token_authenticates_on_user_endpoint(self):
        response = requests.get(f"{self.base_url}/user", headers=self._auth_headers(), timeout=15)
        self.assertEqual(
            200,
            response.status_code,
            (
                "Expected 200 from ClickUp /user endpoint. "
                f"Got {response.status_code}. Response body: {response.text[:300]}"
            ),
        )

        data = response.json()
        self.assertIn("user", data, "Authenticated response does not contain a 'user' object")

    def test_create_task_in_target_list(self):
        due_date_ms = int(datetime(2069, 3, 15, tzinfo=timezone.utc).timestamp() * 1000)
        payload = {
            "name": "test",
            "description": "this is a test description",
            "status": "to do",
            "due_date": due_date_ms,
            "due_date_time": False,
        }

        response = requests.post(
            f"{self.base_url}/list/{TARGET_LIST_ID}/task",
            headers=self._auth_headers(),
            json=payload,
            timeout=15,
        )
        self.assertEqual(
            200,
            response.status_code,
            (
                "Expected 200 from ClickUp task creation endpoint. "
                f"Got {response.status_code}. Response body: {response.text[:500]}"
            ),
        )

        data = response.json()
        self.assertEqual("test", data.get("name"), "Created task name does not match requested value")


if __name__ == "__main__":
    unittest.main()
