#!/usr/bin/env python3
import json
from dataclasses import dataclass
from http.client import HTTPConnection
from typing import Any, Callable, Dict, List, Optional, Tuple


class DeepPlanClientError(RuntimeError):
    def __init__(self, status: int, payload: Dict[str, Any], headers: Dict[str, str]) -> None:
        message = str(payload.get("error", f"http_{status}"))
        super().__init__(message)
        self.status = status
        self.payload = payload
        self.headers = headers


RequestTransport = Callable[[str, str, Optional[Dict[str, Any]], Optional[Dict[str, str]]], Tuple[int, Dict[str, Any], Dict[str, str]]]


def diff_top_level_fields(before: Dict[str, Any], after: Dict[str, Any]) -> List[str]:
    changed: List[str] = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed


def default_transport_factory(host: str, port: int, timeout: float = 10.0) -> RequestTransport:
    def transport(method: str, path: str, body: Optional[Dict[str, Any]], headers: Optional[Dict[str, str]]) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
        connection = HTTPConnection(host, port, timeout=timeout)
        raw_body = None
        merged_headers = dict(headers or {})
        if body is not None:
            raw_body = json.dumps(body).encode("utf-8")
            merged_headers.setdefault("Content-Type", "application/json")
        connection.request(method, path, body=raw_body, headers=merged_headers)
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        response_headers = dict(response.getheaders())
        connection.close()
        return response.status, payload, response_headers

    return transport


@dataclass
class DeepPlanClient:
    transport: RequestTransport
    tracked_fingerprint: str = ""

    @classmethod
    def from_http(cls, host: str = "127.0.0.1", port: int = 8787, timeout: float = 10.0) -> "DeepPlanClient":
        return cls(transport=default_transport_factory(host, port, timeout=timeout))

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        expected_fingerprint: str = "",
        use_tracked_fingerprint: bool = False,
    ) -> Dict[str, Any]:
        headers: Dict[str, str] = {}
        fingerprint = expected_fingerprint or (self.tracked_fingerprint if use_tracked_fingerprint else "")
        if fingerprint:
            headers["If-Match"] = f'"{fingerprint}"'
        status, payload, response_headers = self.transport(method, path, body, headers or None)
        etag = str(response_headers.get("ETag", "")).strip()
        if etag.startswith('"') and etag.endswith('"') and len(etag) >= 2:
            self.tracked_fingerprint = etag[1:-1]
        elif isinstance(payload, dict) and isinstance(payload.get("fingerprint"), str):
            self.tracked_fingerprint = payload["fingerprint"]
        if status >= 400:
            raise DeepPlanClientError(status, payload, response_headers)
        return payload

    def get_plan(self) -> Dict[str, Any]:
        return self.request("GET", "/plan")

    def get_qa(self) -> Dict[str, Any]:
        return self.request("GET", "/qa")

    def get_health(self) -> Dict[str, Any]:
        return self.request("GET", "/health")

    def get_cycle(self, *, history_limit: int = 10) -> Dict[str, Any]:
        return self.request("GET", f"/cycle?limit={int(history_limit)}")

    def get_history(self) -> Dict[str, Any]:
        return self.request("GET", "/history")

    def validate_plan(self) -> Dict[str, Any]:
        return self.request("GET", "/validate")

    def update_plan(self, payload: Dict[str, Any], *, expected_fingerprint: str = "") -> Dict[str, Any]:
        return self.request("POST", "/plan", body=payload, expected_fingerprint=expected_fingerprint, use_tracked_fingerprint=True)

    def replan(self, payload: Dict[str, Any], *, expected_fingerprint: str = "") -> Dict[str, Any]:
        return self.request("POST", "/replan", body=payload, expected_fingerprint=expected_fingerprint, use_tracked_fingerprint=True)

    def add_evidence(self, payload: Dict[str, Any], *, expected_fingerprint: str = "") -> Dict[str, Any]:
        return self.request("POST", "/evidence", body=payload, expected_fingerprint=expected_fingerprint, use_tracked_fingerprint=True)

    def run_tool(self, tool_name: str, payload: Dict[str, Any], *, expected_fingerprint: str = "") -> Dict[str, Any]:
        return self.request("POST", f"/tools/{tool_name}", body={"input": payload}, expected_fingerprint=expected_fingerprint)

    def preview_restore(self, *, revision_id: str = "", previous: bool = False) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if revision_id:
            payload["revision_id"] = revision_id
        if previous:
            payload["previous"] = True
        return self.request("POST", "/restore/preview", body=payload)

    def restore_revision(self, *, revision_id: str = "", previous: bool = False, expected_fingerprint: str = "") -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if revision_id:
            payload["revision_id"] = revision_id
        if previous:
            payload["previous"] = True
        if not expected_fingerprint and self.tracked_fingerprint:
            expected_fingerprint = self.tracked_fingerprint
        return self.request("POST", "/restore", body=payload, expected_fingerprint=expected_fingerprint)

    def capture_evidence_cycle(
        self,
        evidence_payload: Dict[str, Any],
        *,
        replan_payload: Optional[Dict[str, Any]] = None,
        history_limit: int = 10,
    ) -> Dict[str, Any]:
        before = self.get_cycle(history_limit=history_limit)
        evidence_result = self.add_evidence(evidence_payload)
        replan_input = dict(replan_payload or {})
        claim = str(evidence_payload.get("claim", "")).strip()
        source = str(evidence_payload.get("source", "")).strip()
        confidence = evidence_payload.get("confidence")
        axis = str(evidence_payload.get("axis", "")).strip()
        date = str(evidence_payload.get("date", "")).strip()
        if claim and "evidence" not in replan_input:
            replan_input["evidence"] = claim
        if source and "evidence_source" not in replan_input:
            replan_input["evidence_source"] = source
        if isinstance(confidence, int) and not isinstance(confidence, bool) and "evidence_confidence" not in replan_input:
            replan_input["evidence_confidence"] = confidence
        if axis and "evidence_axis" not in replan_input:
            replan_input["evidence_axis"] = axis
        if date and "evidence_date" not in replan_input:
            replan_input["evidence_date"] = date
        replan_result = self.replan(replan_input)
        after = self.get_cycle(history_limit=history_limit)
        before_score = int(before.get("qa", {}).get("score", 0))
        after_score = int(after.get("qa", {}).get("score", 0))
        return {
            "ok": True,
            "operation": "capture_evidence_cycle",
            "result_type": "planning_cycle",
            "pre_fingerprint": before.get("fingerprint", ""),
            "post_fingerprint": after.get("fingerprint", ""),
            "changed_fields": diff_top_level_fields(before.get("plan", {}), after.get("plan", {})),
            "qa_delta": after_score - before_score,
            "evidence_result": evidence_result,
            "replan_result": replan_result,
            "pre_cycle": before,
            "post_cycle": after,
        }
