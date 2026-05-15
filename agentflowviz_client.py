import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def get_backend_url() -> str:
    try:
        import streamlit as st

        return st.session_state.get("backend_url", DEFAULT_BACKEND_URL).rstrip("/")
    except Exception:
        return DEFAULT_BACKEND_URL.rstrip("/")


def api_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = f"{get_backend_url()}/{path.lstrip('/')}"
    timeout = kwargs.pop("timeout", 30)
    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc), "url": url}


def api_get(path: str, **kwargs: Any) -> dict[str, Any]:
    return api_request("GET", path, **kwargs)


def api_post(path: str, json: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    return api_request("POST", path, json=json, **kwargs)


def api_post_multipart(
    path: str,
    data: dict[str, Any],
    files: list[tuple[str, tuple[str, bytes, str]]],
    **kwargs: Any,
) -> dict[str, Any]:
    return api_request("POST", path, data=data, files=files, **kwargs)


def api_patch(path: str, json: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return api_request("PATCH", path, json=json, **kwargs)


def api_delete(path: str, **kwargs: Any) -> dict[str, Any]:
    return api_request("DELETE", path, **kwargs)
