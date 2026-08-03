from __future__ import annotations

import re
import unicodedata


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip().casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def normalize_address(value: str | None) -> str:
    text = normalize_text(value)
    # Padroniza abreviações sem remover número, que é essencial para reincidência.
    replacements = {"avenida": "av", "rua": "r", "travessa": "tv", "numero": "", "n": ""}
    parts = [replacements.get(part, part) for part in text.split()]
    return " ".join(part for part in parts if part)


def client_address_key(client: str | None, address: str | None) -> tuple[str, str]:
    return normalize_text(client), normalize_address(address)


def abbreviate_person(value: str | None) -> str:
    parts = [p for p in (value or "").strip().split() if p]
    if not parts:
        return "Não informado"
    if len(parts) == 1:
        return parts[0]
    ignored = {"da", "de", "do", "das", "dos", "e"}
    significant = [p for p in parts[1:] if p.casefold() not in ignored]
    suffix = significant[-1][0].upper() + "." if significant else parts[-1][0].upper() + "."
    return f"{parts[0]} {suffix}"
