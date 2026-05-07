from flask import jsonify


def success_response(data, *, meta: dict | None = None, status_code: int = 200):
    body = {
        "success": True,
        "data": data,
    }
    if meta:
        body["meta"] = meta
    return jsonify(body), status_code
