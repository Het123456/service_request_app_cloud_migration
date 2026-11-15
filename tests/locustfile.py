"""Locust workload for the Service Request Management Flask app.

Run with the project's official Locust Docker image (see tests/run_load.sh).
Weights: 6 views, 2 creations, 2 status updates. These are task selection
weights, not guaranteed exact percentages of all HTTP requests: on_start and
ID-refresh requests add a small number of GETs.

The app's POST endpoints redirect (302); the script checks that behavior.
A 302 alone cannot prove a database row changed: separately verify data via
SQL during smoke testing and ensure error/failure counts are reviewed.
"""
import os
import random
import re

from locust import HttpUser, between, task

STATUSES = ("Pending", "In Progress", "Completed")
# This identifier must match the exact --tag used by cleanup_load.py.
TEST_TAG = os.environ.get("LOAD_TEST_TAG", "load-test-local-manual")
if not re.fullmatch(r"load-test-[a-zA-Z0-9_-]{1,80}", TEST_TAG):
    raise ValueError("LOAD_TEST_TAG must start with 'load-test-' and use letters, digits, _ or -")

# The application's Jinja template renders forms with action="/update/<id>".
UPDATE_FORM_RE = re.compile(r'action=[\"\']/update/(\d+)[\"\']')


class ServiceDeskUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        self.visible_request_ids = []
        self.refresh_request_ids()

    def refresh_request_ids(self):
        """Record only IDs from an actually rendered requests page."""
        with self.client.get("/", name="GET /", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Expected 200 for request list, got {response.status_code}")
                return
            if "Service Request Management" not in response.text:
                response.failure("Missing expected request-list page heading")
                return
            self.visible_request_ids = [int(value) for value in UPDATE_FORM_RE.findall(response.text)]
            response.success()

    @task(6)
    def view_requests(self):
        self.refresh_request_ids()

    @task(2)
    def add_request(self):
        with self.client.post(
            "/add",
            data={
                "customer_name": TEST_TAG,
                "product_name": "Tata Nexon",
                "issue": "Locust benchmark request",
            },
            name="POST /add",
            allow_redirects=False,
            catch_response=True,
        ) as response:
            if response.status_code != 302 or not response.headers.get("Location", "").endswith("/"):
                response.failure(f"Expected redirect to /, got HTTP {response.status_code}")
            else:
                response.success()

    @task(2)
    def update_status(self):
        if not self.visible_request_ids:
            self.refresh_request_ids()
        if not self.visible_request_ids:
            return  # No existing records: do not manufacture an invalid ID.

        request_id = random.choice(self.visible_request_ids)
        with self.client.post(
            f"/update/{request_id}",
            data={"status": random.choice(STATUSES)},
            name="POST /update",
            allow_redirects=False,
            catch_response=True,
        ) as response:
            if response.status_code != 302 or not response.headers.get("Location", "").endswith("/"):
                response.failure(f"Expected redirect to /, got HTTP {response.status_code}")
            else:
                response.success()
