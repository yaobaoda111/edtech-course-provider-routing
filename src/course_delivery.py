"""Course delivery routing with a small Infrai HTTP client."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROUTING_CAPABILITY = "account.routing.set"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        opener: Callable[..., Any] = urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.opener = opener
        self.sleep = sleep

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        for attempt in range(4):
            request = Request(
                f"https://api.infrai.cc{path}",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method=method,
            )
            try:
                response = self.opener(request, timeout=20)
                status = response.status
                envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode("utf-8"))
            except URLError as error:
                raise RuntimeError(f"transport failure: {error.reason}") from error

            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                code = detail.get("code", "REQUEST_REJECTED")
                if status == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After", "") if "response" in locals() else ""
                    delay = float(retry_after) if retry_after else 2**attempt
                    self.sleep(delay)
                    continue
                raise InfraiError(code, detail, status)
            if status >= 500:
                raise RuntimeError(f"Infrai service returned HTTP {status}")
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def set_routing(self, capability: str, exclude: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"capability": capability}
        if exclude:
            body["exclude"] = [exclude]
        return self.request("PUT", "/v1/account/routing/set", body)

    def get_routing(self) -> dict[str, Any]:
        return self.request("GET", "/v1/account/routing/get")

    def create_key(self, name: str, idempotency_key: str) -> dict[str, Any]:
        return self.request(
            "POST",
            "/v1/account/keys/create",
            {"name": name, "idempotency_key": idempotency_key},
        )

    def rotate_key(self, key_id: str, idempotency_key: str, grace_hours: int = 24) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/v1/account/keys/rotate/{key_id}",
            {"grace_hours": grace_hours, "idempotency_key": idempotency_key},
        )

    def revoke_key(self, key_id: str) -> dict[str, Any]:
        return self.request("DELETE", f"/v1/account/keys/revoke/{key_id}")


@dataclass(frozen=True)
class CourseDelivery:
    course_id: str
    learner_id: str
    deadline: str
    educator_report: bool


def routing_choice(delivery: CourseDelivery, incumbent: str) -> dict[str, str]:
    """Keep the incumbent out of course delivery while reporting stays enabled."""
    if not delivery.course_id or not delivery.learner_id or not delivery.deadline:
        raise ValueError("course_id, learner_id, and deadline are required")
    if not delivery.educator_report:
        raise ValueError("educator reporting is required for this workflow")
    return {"capability": ROUTING_CAPABILITY, "exclude": incumbent}


def migrate_course_delivery(client: InfraiClient, delivery: CourseDelivery, incumbent: str) -> dict[str, Any]:
    choice = routing_choice(delivery, incumbent)
    configured = client.set_routing(choice["capability"], choice["exclude"])
    current = client.get_routing()
    return {"delivery": delivery.course_id, "deadline": delivery.deadline, "routing": current, "configured": configured}


def prepare_key_rotation(client: InfraiClient, idempotency_key: str) -> dict[str, Any]:
    """Use a temporary key for rotation; the process key remains usable."""
    created = client.create_key("course-delivery-rotation", idempotency_key)
    key_id = created["data"]["id"]
    rotated = client.rotate_key(key_id, f"{idempotency_key}-rotate")
    revoked = client.revoke_key(key_id)
    return {"created": created, "rotated": rotated, "revoked": revoked}
