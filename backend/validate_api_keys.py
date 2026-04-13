#!/usr/bin/env python3
"""
Validate multiple AI API keys with provider detection and minimal test calls.

Features:
- Accept API keys via CLI list, file, raw text, and optional screenshot OCR (tesseract)
- Detect provider by key pattern
- Validate key via minimal HTTP call using requests only
- Print status and available models (when endpoint supports it)
- Handle invalid keys, rate limits, and network failures

Examples:
python validate_api_keys.py --keys sk-xxx,nvapi-xxx,sk-ant-xxx,AIzaSyxxx
python validate_api_keys.py --keys-file ./keys.txt
python validate_api_keys.py --raw-text "OPENAI_KEY=sk-abc ... GOOGLE=AIzaSy..."
python validate_api_keys.py --screenshots ./shot1.png ./shot2.jpg

Dummy keys example:
[
  "sk-your-openai-key",
  "nvapi-your-nvidia-key",
  "sk-ant-your-anthropic-key",
  "AIzaSyYourGoogleAIKey",
  "unknown-key-format"
]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import requests


TIMEOUT_SECONDS = 15


class Provider:
    OPENAI = "OpenAI"
    NVIDIA_NIM = "NVIDIA NIM"
    ANTHROPIC = "Anthropic"
    GOOGLE_AI = "Google AI"
    UNKNOWN = "Unknown"


@dataclass
class ValidationResult:
    api_key: str
    provider: str
    status: str
    models: List[str]
    error: Optional[str] = None


def mask_key(key: str) -> str:
    if len(key) <= 8:
        return key
    return f"{key[:4]}...{key[-4:]}"


def detect_provider(key: str) -> str:
    # Anthropic starts with sk-ant- and should be checked before generic sk-
    if key.startswith("sk-ant-"):
        return Provider.ANTHROPIC
    if key.startswith("nvapi-"):
        return Provider.NVIDIA_NIM
    if key.startswith("AIza"):
        return Provider.GOOGLE_AI
    if key.startswith("sk-"):
        return Provider.OPENAI
    return Provider.UNKNOWN


def classify_error(status_code: int, body_text: str) -> str:
    if status_code == 429:
        return "Rate limit"
    if status_code in (401, 403):
        return "Invalid key"
    if status_code >= 500:
        return "Provider server error"

    text = (body_text or "").lower()
    if "rate limit" in text or "quota" in text:
        return "Rate limit"
    if "invalid" in text or "unauthorized" in text or "permission" in text:
        return "Invalid key"
    return f"HTTP {status_code}"


def parse_models(payload: dict) -> List[str]:
    data = payload.get("data")
    if isinstance(data, list):
        models = [m.get("id") for m in data if isinstance(m, dict) and m.get("id")]
        return sorted(set(models))

    models = payload.get("models")
    if isinstance(models, list):
        extracted: List[str] = []
        for item in models:
            if isinstance(item, dict):
                name = item.get("name") or item.get("id")
                if name:
                    extracted.append(str(name))
            elif isinstance(item, str):
                extracted.append(item)
        return sorted(set(extracted))

    return []


def validate_openai(api_key: str) -> ValidationResult:
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    return do_request_validation(api_key, Provider.OPENAI, url, headers=headers)


def validate_nvidia_nim(api_key: str) -> ValidationResult:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    models_url = "https://integrate.api.nvidia.com/v1/models"

    models: List[str] = []
    try:
        models_resp = requests.get(models_url, headers=headers, timeout=TIMEOUT_SECONDS)
        if models_resp.status_code < 400:
            try:
                models = parse_models(models_resp.json())
            except json.JSONDecodeError:
                models = []
    except requests.exceptions.RequestException:
        # Ignore model-list fetch errors; auth probe below determines validity.
        models = []

    # Use a tiny authenticated chat completion probe to avoid false positives from public model listing.
    probe_model = models[0] if models else "meta/llama-3.1-8b-instruct"
    chat_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    payload = {
        "model": probe_model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0,
    }

    try:
        probe_resp = requests.post(
            chat_url,
            headers=headers,
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as exc:
        return ValidationResult(
            api_key=api_key,
            provider=Provider.NVIDIA_NIM,
            status="Invalid",
            models=models,
            error=f"Network failure: {exc}",
        )

    if probe_resp.status_code >= 400:
        return ValidationResult(
            api_key=api_key,
            provider=Provider.NVIDIA_NIM,
            status="Invalid",
            models=models,
            error=classify_error(probe_resp.status_code, probe_resp.text[:500]),
        )

    return ValidationResult(
        api_key=api_key,
        provider=Provider.NVIDIA_NIM,
        status="Valid",
        models=models,
        error=None,
    )


def validate_anthropic(api_key: str) -> ValidationResult:
    url = "https://api.anthropic.com/v1/models"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    return do_request_validation(api_key, Provider.ANTHROPIC, url, headers=headers)


def validate_google_ai(api_key: str) -> ValidationResult:
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    params = {"key": api_key}
    return do_request_validation(api_key, Provider.GOOGLE_AI, url, params=params)


def do_request_validation(
    api_key: str,
    provider: str,
    url: str,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
) -> ValidationResult:
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as exc:
        return ValidationResult(
            api_key=api_key,
            provider=provider,
            status="Invalid",
            models=[],
            error=f"Network failure: {exc}",
        )

    body_text = response.text[:500]

    if response.status_code >= 400:
        return ValidationResult(
            api_key=api_key,
            provider=provider,
            status="Invalid",
            models=[],
            error=classify_error(response.status_code, body_text),
        )

    models: List[str] = []
    try:
        payload = response.json()
        models = parse_models(payload)
    except json.JSONDecodeError:
        # Some endpoints may return non-JSON or empty responses; key can still be valid.
        pass

    return ValidationResult(
        api_key=api_key,
        provider=provider,
        status="Valid",
        models=models,
        error=None,
    )


def validate_key(api_key: str) -> ValidationResult:
    provider = detect_provider(api_key)

    if provider == Provider.OPENAI:
        return validate_openai(api_key)
    if provider == Provider.NVIDIA_NIM:
        return validate_nvidia_nim(api_key)
    if provider == Provider.ANTHROPIC:
        return validate_anthropic(api_key)
    if provider == Provider.GOOGLE_AI:
        return validate_google_ai(api_key)

    return ValidationResult(
        api_key=api_key,
        provider=Provider.UNKNOWN,
        status="Invalid",
        models=[],
        error="Unknown provider pattern",
    )


def extract_keys_from_text(text: str) -> List[str]:
    # Capture common key formats while avoiding heavy false positives.
    patterns = [
        r"sk-ant-[A-Za-z0-9_\-]{10,}",
        r"nvapi-[A-Za-z0-9_\-]{10,}",
        r"AIza[0-9A-Za-z_\-]{20,}",
        r"sk-[A-Za-z0-9_\-]{16,}",
    ]

    found: List[str] = []
    for pattern in patterns:
        found.extend(re.findall(pattern, text))

    # Deduplicate while preserving order.
    deduped = list(dict.fromkeys(found))
    return deduped


def extract_text_from_screenshot(image_path: str) -> Tuple[str, Optional[str]]:
    tesseract_path = shutil.which("tesseract")
    if not tesseract_path:
        return "", "tesseract not found in PATH"

    try:
        result = subprocess.run(
            [tesseract_path, image_path, "stdout", "-l", "eng"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return "", f"failed to execute tesseract: {exc}"

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return "", f"OCR failed: {stderr or 'unknown error'}"

    return result.stdout or "", None


def collect_input_keys(args: argparse.Namespace) -> Tuple[List[str], List[str]]:
    keys: List[str] = []
    notes: List[str] = []

    if args.keys:
        for item in args.keys.split(","):
            k = item.strip()
            if k:
                keys.append(k)

    if args.keys_file:
        try:
            with open(args.keys_file, "r", encoding="utf-8") as f:
                for line in f:
                    k = line.strip()
                    if k and not k.startswith("#"):
                        keys.append(k)
        except OSError as exc:
            notes.append(f"Could not read keys file {args.keys_file}: {exc}")

    if args.raw_text:
        keys.extend(extract_keys_from_text(args.raw_text))

    if args.screenshots:
        for shot in args.screenshots:
            text, err = extract_text_from_screenshot(shot)
            if err:
                notes.append(f"Screenshot OCR warning for {shot}: {err}")
                continue
            keys.extend(extract_keys_from_text(text))

    # Final cleanup and dedupe.
    cleaned = [k.strip().strip('"\'') for k in keys if k.strip()]
    deduped = list(dict.fromkeys(cleaned))
    return deduped, notes


def print_result(result: ValidationResult) -> None:
    print(f"API Key: {mask_key(result.api_key)}")
    print(f"Provider: {result.provider}")
    print(f"Status: {result.status}")
    if result.models:
        print(f"Models: {', '.join(result.models[:25])}")
    else:
        print("Models: N/A")
    if result.error:
        print(f"Error: {result.error}")
    print("-" * 50)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate multiple AI API keys and identify provider/model access.",
    )
    parser.add_argument(
        "--keys",
        default="",
        help="Comma-separated API keys.",
    )
    parser.add_argument(
        "--keys-file",
        default="",
        help="Text file with one key per line.",
    )
    parser.add_argument(
        "--raw-text",
        default="",
        help="Raw text (for pasted OCR output) to extract keys from.",
    )
    parser.add_argument(
        "--screenshots",
        nargs="*",
        default=[],
        help="Screenshot image paths. Requires tesseract installed.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    keys, notes = collect_input_keys(args)

    for note in notes:
        print(f"Note: {note}")

    if not keys:
        print("No API keys found in input.")
        print("Tip: Use --keys, --keys-file, --raw-text, or --screenshots.")
        return 1

    for key in keys:
        result = validate_key(key)
        print_result(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
