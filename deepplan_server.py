#!/usr/bin/env python3
import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from deepplan import add_evidence, load_plan, plan_summary, qa_report, save_plan


def merge_plan_updates(plan: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    scalar_fields = [
        "goal",
        "success_metric",
        "deadline",
        "planning_horizon",
        "review_cadence",
        "selected_option",
    ]
    list_fields = [
        "phase_plan",
        "constraints",
        "assumptions",
        "options",
        "plan_tasks",
        "execution_tasks",
        "dependencies",
        "experiments",
        "risks",
        "references",
        "insights",
        "direction_insights",
        "market_insights",
        "timing_insights",
        "differentiation_insights",
        "monetization_insights",
        "constraint_insights",
        "risk_signal_insights",
        "evolution_insights",
        "definition_of_done",
    ]

    for field in scalar_fields:
        if field in payload and isinstance(payload[field], str):
            plan[field] = payload[field].strip()
    for field in list_fields:
        if field in payload and isinstance(payload[field], list):
            plan[field] = payload[field]
    return plan


class DeepPlanHandler(BaseHTTPRequestHandler):
    server_version = "DeepPlanHTTP/0.1"

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write_json(HTTPStatus.OK, {"status": "ok"})
            return
        if self.path == "/plan":
            plan = load_plan()
            self._write_json(HTTPStatus.OK, {"plan": plan, "summary": plan_summary(plan)})
            return
        if self.path == "/qa":
            plan = load_plan()
            self._write_json(HTTPStatus.OK, qa_report(plan))
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        payload = self._read_json()
        if payload is None:
            return

        if self.path == "/plan":
            plan = load_plan()
            plan = merge_plan_updates(plan, payload)
            save_plan(plan)
            self._write_json(
                HTTPStatus.OK,
                {"plan": plan, "summary": plan_summary(plan), "qa": qa_report(plan)},
            )
            return

        if self.path == "/evidence":
            claim = str(payload.get("claim", "")).strip()
            if not claim:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": "claim is required"})
                return
            plan = load_plan()
            add_evidence(
                plan,
                claim,
                str(payload.get("source", "api")).strip() or "api",
                int(payload.get("confidence", 60)),
                str(payload.get("axis", "")).strip(),
                str(payload.get("date", "")).strip(),
            )
            if isinstance(payload.get("reference"), str) and payload["reference"].strip():
                plan.setdefault("references", []).append(payload["reference"].strip())
            save_plan(plan)
            self._write_json(
                HTTPStatus.OK,
                {"plan": plan, "summary": plan_summary(plan), "qa": qa_report(plan)},
            )
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> Optional[Dict[str, Any]]:
        length = self.headers.get("Content-Length", "0")
        try:
            raw_length = int(length)
        except ValueError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_content_length"})
            return None

        body = self.rfile.read(raw_length) if raw_length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return None
        if not isinstance(payload, dict):
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "json_body_must_be_object"})
            return None
        return payload

    def _write_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DeepPlan minimal HTTP service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DeepPlanHandler)
    print(f"DeepPlan service listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
