from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

CKAN_BASE_URL = "https://ckan.pbh.gov.br/api/3/action"
PACKAGE_ID = "vagas-ofertadas-pbh"
MINIMUM_COLUMNS = {"DATA", "OCUPAÇÃO", "NÚMERO DE VAGAS"}
MAPPING_COLUMNS = (
    "nome_original_referencia",
    "nome_chave_normalizada",
    "nome_padronizado",
    "codigo_cbo",
    "status_validacao",
    "criterio_correspondencia",
)


def occupation_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def normalize_text(value: str) -> str:
    normalized = (value or "").replace("º", "N").replace("ª", "A")
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = " ".join(normalized.replace("*", " ").split())
    return normalized.upper()


def parse_brazilian_date(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%d/%m/%Y")


def parse_vacancy_count(value: str) -> int:
    cleaned = (value or "").strip().replace(".", "").replace(",", ".")
    try:
        return int(float(cleaned))
    except (TypeError, ValueError):
        return 0


def quarter_label(date: datetime) -> str:
    return f"{date.year}-T{((date.month - 1) // 3) + 1}"


def ckan_get(action: str, params: dict[str, str] | None = None) -> dict:
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    request = urllib.request.Request(
        f"{CKAN_BASE_URL}/{action}{query}",
        headers={"User-Agent": "EmpregaBH-pipeline/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if not payload.get("success"):
        raise RuntimeError(f"CKAN action {action} failed")
    return payload["result"]


def discover_resources() -> list[dict]:
    package = ckan_get("package_show", {"id": PACKAGE_ID})
    return [
        resource
        for resource in package.get("resources", [])
        if str(resource.get("format", "")).upper() == "CSV"
        and resource.get("url")
    ]


def download_csv(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 EmpregaBH/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        content = response.read()
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", content, 0, len(content), "unsupported CSV encoding")


def normalize_csv_text(text: str) -> list[dict[str, str]]:
    for delimiter in (";", ","):
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        if reader.fieldnames:
            fieldnames = {normalize_text(name): name for name in reader.fieldnames}
            vacancy_aliases = {"NUMERO DE VAGAS", "N DE VAGAS", "NN DE VAGAS", "NRO DE VAGAS"}
            vacancy_column = next((name for name in fieldnames if "DE VAGAS" in name), None)
            if "DATA" in fieldnames and "OCUPACAO" in fieldnames and vacancy_column:
                rows = []
                for raw_row in reader:
                    row = {normalize_text(name): (raw_row[name] or "").strip() for name in reader.fieldnames}
                    vacancy_column = next((key for key in row if "DE VAGAS" in key), None)
                    if vacancy_column:
                        row["NUMERO DE VAGAS"] = row[vacancy_column]
                    rows.append(row)
                return rows
    raise ValueError("CSV does not contain DATA, OCUPAÇÃO and NÚMERO DE VAGAS")


def load_equivalence_dictionary(path: Path) -> dict[str, dict[str, str]]:
    mappings: dict[str, dict[str, str]] = {}
    if not path.exists():
        raise FileNotFoundError(f"Dicionário de ocupações não encontrado: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != MAPPING_COLUMNS:
            raise ValueError("Estrutura inválida do dicionário de ocupações")
        for row in reader:
            key = occupation_key(row["nome_chave_normalizada"])
            if not key:
                continue
            if key in mappings:
                raise ValueError(f"Chave duplicada no dicionário de ocupações: {key}")
            status = row["status_validacao"].strip().lower()
            if status not in {"validado", "pendente", "nao_mapeado"}:
                raise ValueError(f"Status inválido no dicionário de ocupações: {status}")
            criterion = row["criterio_correspondencia"].strip().lower()
            if criterion not in {"titulo_oficial", "sinonimo_cbo", "validacao_manual"}:
                raise ValueError(f"Critério inválido no dicionário de ocupações: {criterion}")
            if status == "validado":
                if not row["nome_padronizado"].strip() or not row["codigo_cbo"].strip():
                    raise ValueError(f"Mapeamento validado incompleto para a chave: {key}")
            mappings[key] = row
    return mappings


def apply_occupation_mapping(original: str, mappings: dict[str, dict[str, str]]) -> dict[str, str]:
    key = occupation_key(original)
    mapping = mappings.get(key)
    if mapping and mapping["status_validacao"].strip().lower() == "validado":
        return {
            "nome_ocupacao_original": original,
            "nome_chave_normalizada": key,
            "nome_padronizado": mapping["nome_padronizado"].strip(),
            "codigo_cbo": str(mapping["codigo_cbo"]).strip(),
            "status_validacao": "validado",
        }
    if mapping:
        return {
            "nome_ocupacao_original": original,
            "nome_chave_normalizada": key,
            "nome_padronizado": original,
            "codigo_cbo": "",
            "status_validacao": mapping["status_validacao"].strip().lower(),
        }
    return {
        "nome_ocupacao_original": original,
        "nome_chave_normalizada": key,
        "nome_padronizado": original,
        "codigo_cbo": "",
        "status_validacao": "nao_mapeado",
    }


def clean_and_deduplicate(rows: Iterable[dict[str, str]], mappings: dict[str, dict[str, str]] | None = None) -> list[dict[str, str]]:
    mappings = mappings or {}
    cleaned = []
    seen: set[tuple] = set()
    for row in rows:
        occupation = normalize_text(row["OCUPACAO"] if "OCUPACAO" in row else row.get("OCUPAÇÃO", ""))
        try:
            date = parse_brazilian_date(row["DATA"])
        except (KeyError, ValueError):
            continue
        if date.year < 2021 or date.year > datetime.now().year:
            continue
        vacancy_count = parse_vacancy_count(row["NUMERO DE VAGAS"] if "NUMERO DE VAGAS" in row else row.get("NÚMERO DE VAGAS", ""))
        if not occupation or vacancy_count < 0:
            continue
        key = (
            date.strftime("%Y-%m-%d"),
            occupation,
            normalize_text(row.get("LOCAL DE TRABALHO", "")),
            vacancy_count,
            normalize_text(row.get("ESCOLARIDADE", "")),
            normalize_text(row.get("EXPERIÊNCIA", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        mapped = apply_occupation_mapping(row["OCUPACAO"] if "OCUPACAO" in row else row.get("OCUPAÇÃO", ""), mappings)
        cleaned.append({
            "date": date,
            "quarter": quarter_label(date),
            **mapped,
            "cbo": mapped["codigo_cbo"],
            "vacancies": vacancy_count,
        })
    return cleaned


def aggregate(rows: Iterable[dict]) -> list[dict]:
    totals: dict[tuple[str, str, str, str, str], int] = defaultdict(int)
    for row in rows:
        if row["codigo_cbo"]:
            internal_key = f"cbo:{row['codigo_cbo']}"
        else:
            internal_key = f"ocupacao:{row['nome_chave_normalizada']}"
        identity = (
            internal_key,
            row["nome_padronizado"],
            row["codigo_cbo"],
            row["status_validacao"],
            row["quarter"],
        )
        totals[identity] += row["vacancies"]
    return [
        {
            "nome_padronizado": identity[1],
            "codigo_cbo": identity[2],
            "status_validacao": identity[3],
            "quarter": identity[4],
            "vacancies": vacancies,
        }
        for identity, vacancies in sorted(totals.items(), key=lambda item: (item[0][4], item[0][1]))
    ]


def write_processed_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["nome_padronizado", "codigo_cbo", "status_validacao", "quarter", "vacancies"])
        writer.writeheader()
        writer.writerows(rows)


def write_review_csv(path: Path, cleaned_rows: list[dict]) -> None:
    counts: dict[str, dict] = {}
    for row in cleaned_rows:
        key = row["nome_chave_normalizada"]
        item = counts.setdefault(key, {
            "nome_ocupacao_original": row["nome_ocupacao_original"],
            "nome_chave_normalizada": key,
            "quantidade_registros": 0,
            "trimestres": set(),
            "status": row["status_validacao"],
        })
        item["quantidade_registros"] += 1
        item["trimestres"].add(row["quarter"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["nome_ocupacao_original", "nome_chave_normalizada", "quantidade_registros", "trimestres", "status"])
        writer.writeheader()
        for item in sorted(counts.values(), key=lambda value: value["nome_chave_normalizada"]):
            if item["status"] in {"pendente", "nao_mapeado"}:
                writer.writerow({**item, "trimestres": ";".join(sorted(item["trimestres"]))})


def write_manifest(path: Path, resources: list[dict], collected_at: str, source_sha256: str, mapping: Path) -> None:
    manifest = {
        "package_id": PACKAGE_ID,
        "package_url": f"{CKAN_BASE_URL}/package_show?id={PACKAGE_ID}",
        "collected_at": collected_at,
        "resource_count": len(resources),
        "source_bundle_sha256": source_sha256,
        "occupation_mapping": {
            "path": str(mapping),
            "sha256": hashlib.sha256(mapping.read_bytes()).hexdigest(),
        },
        "resources": [
            {
                "id": resource.get("id"),
                "name": resource.get("name"),
                "url": resource.get("url"),
            }
            for resource in resources
        ],
        "privacy": ["CNPJ and IDENTIFICACAO are excluded from processed output"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def run(output: Path, manifest: Path, mapping: Path, review: Path) -> tuple[int, int, str]:
    resources = discover_resources()
    mappings = load_equivalence_dictionary(mapping)
    all_cleaned = []
    bundle = hashlib.sha256()
    for resource in resources:
        text = download_csv(resource["url"])
        bundle.update(resource["url"].encode("utf-8"))
        bundle.update(text.encode("utf-8"))
        try:
            normalized_rows = normalize_csv_text(text)
        except ValueError:
            continue
        all_cleaned.extend(clean_and_deduplicate(normalized_rows, mappings))
    aggregated = aggregate(all_cleaned)
    write_processed_csv(output, aggregated)
    write_review_csv(review, all_cleaned)
    collected_at = datetime.now().astimezone().isoformat(timespec="seconds")
    write_manifest(manifest, resources, collected_at, bundle.hexdigest(), mapping)
    return len(resources), len(aggregated), collected_at


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract and aggregate PBH vacancy data")
    parser.add_argument("--output", type=Path, default=Path("data/processed/vagas_por_ocupacao_trimestre.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/local/vagas_ckan_manifest.json"))
    parser.add_argument("--mapping", type=Path, default=Path("pipeline/mapeamento_ocupacoes_cbo.csv"))
    parser.add_argument("--review", type=Path, default=Path("reports/local/ocupacoes_para_revisao.csv"))
    args = parser.parse_args()
    try:
        resource_count, row_count, collected_at = run(args.output, args.manifest, args.mapping, args.review)
    except Exception as exc:
        print(f"Erro na coleta CKAN: {exc}", file=sys.stderr)
        return 1
    print(f"Coletados {resource_count} recursos; geradas {row_count} linhas agregadas em {args.output}")
    print(f"Manifesto: {args.manifest}; coleta: {collected_at}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
