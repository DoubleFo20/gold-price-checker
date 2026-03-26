"""routes/jobs.py — Job runner and web-push public key endpoints."""
import os
import hmac
import traceback
from flask import Blueprint, jsonify, request
from services.scheduler import run_scheduled_jobs_once

jobs_bp = Blueprint("jobs", __name__)


def _job_token_ok(req) -> bool:
    expected = (os.getenv("JOB_TOKEN") or "").strip()
    if not expected:
        return False
    auth = (req.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        got = auth.split(" ", 1)[1].strip()
        return hmac.compare_digest(got, expected)
    got = (req.headers.get("X-Job-Token") or "").strip()
    if got:
        return hmac.compare_digest(got, expected)
    return False


@jobs_bp.route("/api/jobs/run", methods=["POST"])
def api_run_jobs():
    if not _job_token_ok(request):
        return jsonify(ok=False, message="Unauthorized"), 401
    try:
        result = run_scheduled_jobs_once()
        return jsonify(result), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify(ok=False, message=str(e)), 200


@jobs_bp.route("/api/web-push/public-key", methods=["GET"])
def web_push_public_key():
    key = (os.getenv("VAPID_PUBLIC_KEY") or "").strip()
    return jsonify(success=True, public_key=key), 200
