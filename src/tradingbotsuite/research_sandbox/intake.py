from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pandas as pd

from tradingbotsuite.research_sandbox.spec import DataWindow, SandboxRunSpec, StrategyCatalogRow, VenueArchiveDescriptor
from tradingbotsuite.research_sandbox.strategy_blueprints import (
    compile_spreadsheet_lead_frame,
    compile_strategy_config_payload,
    is_spreadsheet_lead_frame,
)


REQUIRED_STRATEGY_COLUMNS = {"hypothesis_id", "family", "signal_column"}
WORKBOOK_STRATEGY_CATALOG_SUFFIXES = frozenset({".xlsx"})
LEGACY_XLS_STRATEGY_CATALOG_SUFFIXES = frozenset({".xls"})
SUPPORTED_STRATEGY_CATALOG_SUFFIXES = frozenset({".csv", ".tsv", ".json", ".parquet", *WORKBOOK_STRATEGY_CATALOG_SUFFIXES})
RECOGNIZED_STRATEGY_CATALOG_SUFFIXES = frozenset(
    {*SUPPORTED_STRATEGY_CATALOG_SUFFIXES, *LEGACY_XLS_STRATEGY_CATALOG_SUFFIXES}
)
MAX_WORKBOOK_SHEET_SAMPLE = 20
MAX_XLSX_ZIP_MEMBERS = 256
MAX_XLSX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_XLSX_TOTAL_XML_BYTES = 32 * 1024 * 1024
MAX_XLSX_SHEETS = 64
MAX_XLSX_SHARED_STRINGS = 100_000
MAX_XLSX_ROWS_PER_SHEET = 20_000
MAX_XLSX_CELLS_PER_SHEET = 250_000
MAX_XLSX_COLUMNS_PER_SHEET = 512
DIRECT_STRATEGY_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "hypothesis_id": (
        "hypothesis_id",
        "hypothesis",
        "hypothesisid",
        "hypothesis_name",
        "hypothesisname",
        "strategy_id",
        "strategyid",
        "strategy_name",
        "strategyname",
        "candidate",
        "candidate_id",
        "candidateid",
        "lead_id",
        "leadid",
        "idea",
        "idea_id",
        "ideaid",
    ),
    "family": (
        "family",
        "family_id",
        "familyid",
        "strategy_family",
        "strategyfamily",
        "category",
        "theme",
        "group",
    ),
    "signal_column": (
        "signal_column",
        "signalcolumn",
        "signal",
        "signal_col",
        "signalcol",
        "signal_name",
        "signalname",
        "entry_signal",
        "entrysignal",
        "entry_column",
        "entrycolumn",
        "column_name",
        "columnname",
        "feature_signal",
        "featuresignal",
    ),
    "side": ("side", "direction", "trade_side", "tradeside", "bias", "position_side", "positionside"),
    "source_id": ("source_id", "sourceid", "source", "source_name", "sourcename", "origin", "catalog_source", "catalogsource"),
    "exit_profile": ("exit_profile", "exitprofile", "exit", "exit_type", "exittype"),
    "filter_column": (
        "filter_column",
        "filtercolumn",
        "filter",
        "filter_col",
        "filtercol",
        "quality_filter",
        "qualityfilter",
    ),
    "filter_min": ("filter_min", "filtermin", "min_filter", "minfilter", "filter_lower", "filterlower"),
    "filter_max": ("filter_max", "filtermax", "max_filter", "maxfilter", "filter_upper", "filterupper"),
    "params_json": ("params_json", "paramsjson", "param_json", "paramjson", "parameters_json", "parametersjson"),
    "params": ("params", "parameters"),
    "tags": ("tags", "tag", "labels", "label"),
    "notes": ("notes", "note", "description", "comment", "comments"),
}


def _xlsx_fallback_limits() -> dict[str, int]:
    return {
        "max_xlsx_zip_members": MAX_XLSX_ZIP_MEMBERS,
        "max_xlsx_member_bytes": MAX_XLSX_MEMBER_BYTES,
        "max_xlsx_total_xml_bytes": MAX_XLSX_TOTAL_XML_BYTES,
        "max_xlsx_sheets": MAX_XLSX_SHEETS,
        "max_xlsx_shared_strings": MAX_XLSX_SHARED_STRINGS,
        "max_xlsx_rows_per_sheet": MAX_XLSX_ROWS_PER_SHEET,
        "max_xlsx_cells_per_sheet": MAX_XLSX_CELLS_PER_SHEET,
        "max_xlsx_columns_per_sheet": MAX_XLSX_COLUMNS_PER_SHEET,
    }


def _raise_unsupported_legacy_xls(path: Path) -> None:
    raise ValueError(
        "unsupported_legacy_xls_strategy_catalog: "
        f"{path}; convert legacy .xls inputs to .xlsx, .csv, .tsv, .json, or .parquet"
    )


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or value == ""


def _optional_str(value: Any) -> str | None:
    if _is_missing(value):
        return None
    return str(value)


def _optional_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    return float(value)


def _parse_jsonish(value: Any, *, field_name: str) -> dict[str, Any]:
    if _is_missing(value):
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field_name} must be JSON object text") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{field_name} must decode to a JSON object")
        return parsed
    raise TypeError(f"{field_name} must be a mapping or JSON object text")


def _parse_tags(value: Any) -> tuple[str, ...]:
    if _is_missing(value):
        return ()
    if isinstance(value, str):
        return tuple(item.strip() for item in re.split(r"[|,;]", value) if item.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return (str(value),)


def _normalized_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _direct_strategy_alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in DIRECT_STRATEGY_COLUMN_ALIASES.items():
        for alias in aliases:
            lookup[_normalized_header(alias)] = canonical
    return lookup


def _canonical_strategy_catalog_frame(frame: pd.DataFrame) -> pd.DataFrame:
    alias_lookup = _direct_strategy_alias_lookup()
    claimed: set[str] = set()
    renames: dict[Any, str] = {}
    for column in frame.columns:
        canonical = alias_lookup.get(_normalized_header(column))
        if canonical is None or canonical in claimed:
            continue
        claimed.add(canonical)
        if str(column) != canonical:
            renames[column] = canonical
    return frame.rename(columns=renames) if renames else frame


def _has_direct_strategy_columns(frame: pd.DataFrame) -> bool:
    return REQUIRED_STRATEGY_COLUMNS.issubset(_canonical_strategy_catalog_frame(frame).columns)


def _sheet_frame_with_source(frame: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    output = frame.copy()
    output["source_sheet"] = sheet_name
    return output


def _excel_sheet_frames(path: Path) -> list[tuple[str, pd.DataFrame]]:
    if path.suffix.lower() in LEGACY_XLS_STRATEGY_CATALOG_SUFFIXES:
        _raise_unsupported_legacy_xls(path)
    try:
        workbook = pd.ExcelFile(path)
    except ImportError:
        if path.suffix.lower() == ".xlsx":
            return _load_xlsx_sheet_frames_without_optional_engine(path)
        raise
    try:
        return [(str(sheet_name), workbook.parse(sheet_name=sheet_name)) for sheet_name in workbook.sheet_names]
    finally:
        close = getattr(workbook, "close", None)
        if close is not None:
            close()


def _load_excel_table(path: Path) -> pd.DataFrame:
    sheets = _excel_sheet_frames(path)
    first_frame: pd.DataFrame | None = None
    first_sheet_name: str | None = None
    for sheet_name, frame in sheets:
        if first_frame is None:
            first_frame = frame
            first_sheet_name = sheet_name
        if _has_direct_strategy_columns(frame) or is_spreadsheet_lead_frame(frame):
            return _sheet_frame_with_source(frame, sheet_name)
    if first_frame is None:
        raise ValueError(f"spreadsheet strategy catalog is empty: {path}")
    return _sheet_frame_with_source(first_frame, first_sheet_name or "Sheet1")


def _load_xlsx_table_without_optional_engine(path: Path) -> pd.DataFrame:
    sheets = _load_xlsx_sheet_frames_without_optional_engine(path)
    first_frame: pd.DataFrame | None = None
    first_sheet_name: str | None = None
    for sheet_name, frame in sheets:
        if first_frame is None:
            first_frame = frame
            first_sheet_name = sheet_name
        if _has_direct_strategy_columns(frame) or is_spreadsheet_lead_frame(frame):
            return _sheet_frame_with_source(frame, sheet_name)
    if first_frame is None:
        raise ValueError(f"spreadsheet strategy catalog is empty: {path}")
    return _sheet_frame_with_source(first_frame, first_sheet_name or "Sheet1")


def _load_xlsx_sheet_frames_without_optional_engine(path: Path) -> list[tuple[str, pd.DataFrame]]:
    with zipfile.ZipFile(path) as archive:
        _validate_xlsx_zip_member_count(archive)
        read_state = {"xml_bytes_read": 0}
        shared_strings = _xlsx_shared_strings(archive, read_state)
        sheets = _xlsx_sheet_paths(archive, read_state)
        if len(sheets) > MAX_XLSX_SHEETS:
            raise ValueError(f"xlsx_sheet_count_limit_exceeded: {len(sheets)} > {MAX_XLSX_SHEETS}")
        frames = [
            (sheet_name, _xlsx_sheet_frame(archive, sheet_path, shared_strings, read_state))
            for sheet_name, sheet_path in sheets
        ]
    if not frames:
        raise ValueError(f"spreadsheet strategy catalog is empty: {path}")
    return frames


def _validate_xlsx_zip_member_count(archive: zipfile.ZipFile) -> None:
    member_count = len(archive.infolist())
    if member_count > MAX_XLSX_ZIP_MEMBERS:
        raise ValueError(f"xlsx_member_count_limit_exceeded: {member_count} > {MAX_XLSX_ZIP_MEMBERS}")


def _normalize_xlsx_member_path(member_name: str) -> str:
    normalized = member_name.replace("\\", "/").lstrip("/")
    parts = [part for part in normalized.split("/") if part]
    if not parts or any(part == ".." for part in parts):
        raise ValueError(f"xlsx_unsafe_member_path: {member_name}")
    return "/".join(parts)


def _xlsx_read_xml_member(
    archive: zipfile.ZipFile,
    member_name: str,
    read_state: dict[str, int],
    *,
    required: bool = True,
) -> bytes:
    normalized = _normalize_xlsx_member_path(member_name)
    try:
        info = archive.getinfo(normalized)
    except KeyError:
        if required:
            raise
        return b""
    if info.file_size > MAX_XLSX_MEMBER_BYTES:
        raise ValueError(f"xlsx_member_bytes_limit_exceeded: {normalized} {info.file_size} > {MAX_XLSX_MEMBER_BYTES}")
    projected_total = read_state.get("xml_bytes_read", 0) + info.file_size
    if projected_total > MAX_XLSX_TOTAL_XML_BYTES:
        raise ValueError(
            f"xlsx_total_xml_bytes_limit_exceeded: {projected_total} > {MAX_XLSX_TOTAL_XML_BYTES}"
        )
    with archive.open(info) as handle:
        payload = handle.read(MAX_XLSX_MEMBER_BYTES + 1)
    if len(payload) > MAX_XLSX_MEMBER_BYTES:
        raise ValueError(f"xlsx_member_bytes_limit_exceeded: {normalized} > {MAX_XLSX_MEMBER_BYTES}")
    read_state["xml_bytes_read"] = read_state.get("xml_bytes_read", 0) + len(payload)
    if read_state["xml_bytes_read"] > MAX_XLSX_TOTAL_XML_BYTES:
        raise ValueError(
            f"xlsx_total_xml_bytes_limit_exceeded: {read_state['xml_bytes_read']} > {MAX_XLSX_TOTAL_XML_BYTES}"
        )
    return payload


def _xlsx_shared_strings(archive: zipfile.ZipFile, read_state: dict[str, int]) -> list[str]:
    payload = _xlsx_read_xml_member(archive, "xl/sharedStrings.xml", read_state, required=False)
    if not payload:
        return []
    root = ET.fromstring(payload)
    values: list[str] = []
    for item in root.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
        if len(values) >= MAX_XLSX_SHARED_STRINGS:
            raise ValueError(
                f"xlsx_shared_strings_limit_exceeded: more than {MAX_XLSX_SHARED_STRINGS} shared strings"
            )
        texts = item.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
        values.append("".join(text.text or "" for text in texts))
    return values


def _xlsx_sheet_paths(archive: zipfile.ZipFile, read_state: dict[str, int]) -> list[tuple[str, str]]:
    workbook = ET.fromstring(_xlsx_read_xml_member(archive, "xl/workbook.xml", read_state))
    rels = ET.fromstring(_xlsx_read_xml_member(archive, "xl/_rels/workbook.xml.rels", read_state))
    rel_targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
    }
    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"):
        name = sheet.attrib.get("name", "Sheet")
        rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        if not rel_id or rel_id not in rel_targets:
            continue
        target = _normalize_xlsx_member_path(rel_targets[rel_id])
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        sheets.append((name, _normalize_xlsx_member_path(target)))
    return sheets


def _xlsx_sheet_frame(
    archive: zipfile.ZipFile,
    sheet_path: str,
    shared_strings: list[str],
    read_state: dict[str, int],
) -> pd.DataFrame:
    root = ET.fromstring(_xlsx_read_xml_member(archive, sheet_path, read_state))
    rows: list[list[Any]] = []
    max_width = 0
    row_count = 0
    cell_count = 0
    for row in root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
        row_count += 1
        if row_count > MAX_XLSX_ROWS_PER_SHEET:
            raise ValueError(f"xlsx_sheet_rows_limit_exceeded: {row_count} > {MAX_XLSX_ROWS_PER_SHEET}")
        values: dict[int, Any] = {}
        for cell in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
            cell_count += 1
            if cell_count > MAX_XLSX_CELLS_PER_SHEET:
                raise ValueError(f"xlsx_sheet_cells_limit_exceeded: {cell_count} > {MAX_XLSX_CELLS_PER_SHEET}")
            ref = cell.attrib.get("r", "")
            column_index = _xlsx_column_index(ref)
            if column_index is None:
                continue
            if column_index >= MAX_XLSX_COLUMNS_PER_SHEET:
                raise ValueError(
                    f"xlsx_sheet_columns_limit_exceeded: {column_index + 1} > {MAX_XLSX_COLUMNS_PER_SHEET}"
                )
            values[column_index] = _xlsx_cell_value(cell, shared_strings)
        if values:
            width = max(values) + 1
            max_width = max(max_width, width)
            rows.append([values.get(index) for index in range(width)])
    if not rows:
        return pd.DataFrame()
    padded = [row + [None] * (max_width - len(row)) for row in rows]
    header_index = next((index for index, row in enumerate(padded) if any(not _is_missing(value) for value in row)), 0)
    headers = [str(value).strip() if not _is_missing(value) else f"Unnamed: {index}" for index, value in enumerate(padded[header_index])]
    data = padded[header_index + 1 :]
    return pd.DataFrame(data, columns=headers)


def _xlsx_column_index(cell_ref: str) -> int | None:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return None
    index = 0
    for char in match.group(1):
        index = (index * 26) + (ord(char) - ord("A") + 1)
    return index - 1


def _xlsx_cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
    if cell_type == "inlineStr":
        texts = cell.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
        return "".join(text.text or "" for text in texts)
    if value_node is None or value_node.text is None:
        return None
    value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return value
    if cell_type in {"str", "b"}:
        return value
    try:
        number = float(value)
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


def _load_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in LEGACY_XLS_STRATEGY_CATALOG_SUFFIXES:
        _raise_unsupported_legacy_xls(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".tsv":
        return pd.read_csv(path, sep="\t")
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("strategies", payload) if isinstance(payload, dict) else payload
        return pd.DataFrame(rows)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in WORKBOOK_STRATEGY_CATALOG_SUFFIXES:
        return _load_excel_table(path)
    raise ValueError(f"unsupported sandbox strategy catalog format: {path.suffix}")


def _strategy_rows_from_direct_frame(source_frame: pd.DataFrame, catalog_path: Path) -> list[StrategyCatalogRow]:
    frame = _canonical_strategy_catalog_frame(source_frame)
    missing = REQUIRED_STRATEGY_COLUMNS.difference(frame.columns)
    if missing:
        joined = ", ".join(sorted(missing))
        raise ValueError(f"strategy catalog missing required columns: {joined}")

    rows: list[StrategyCatalogRow] = []
    for index, record in frame.reset_index(drop=True).iterrows():
        payload = record.to_dict()
        source_id = _optional_str(payload.get("source_id"))
        if source_id is None:
            source_sheet = _optional_str(payload.get("source_sheet"))
            source_id = f"{catalog_path}#{source_sheet}" if source_sheet else str(catalog_path)
        rows.append(
            StrategyCatalogRow(
                hypothesis_id=str(payload["hypothesis_id"]),
                family=str(payload["family"]),
                source_id=source_id,
                signal_column=str(payload["signal_column"]),
                side=_optional_str(payload.get("side")) or "long",
                exit_profile=_optional_str(payload.get("exit_profile")) or "fixed_hold",
                filter_column=_optional_str(payload.get("filter_column")),
                filter_min=_optional_float(payload.get("filter_min")),
                filter_max=_optional_float(payload.get("filter_max")),
                params=_parse_jsonish(payload.get("params_json", payload.get("params")), field_name=f"params row {index}"),
                tags=_parse_tags(payload.get("tags")),
                notes=_optional_str(payload.get("notes")) or "",
            )
        )
    return rows


def _strategy_rows_from_table(source_frame: pd.DataFrame, catalog_path: Path) -> list[StrategyCatalogRow]:
    frame = _canonical_strategy_catalog_frame(source_frame)
    missing = REQUIRED_STRATEGY_COLUMNS.difference(frame.columns)
    if missing:
        compiled = compile_spreadsheet_lead_frame(source_frame, source_path=catalog_path)
        if compiled:
            return compiled
        joined = ", ".join(sorted(missing))
        raise ValueError(f"strategy catalog missing required columns: {joined}")
    return _strategy_rows_from_direct_frame(frame, catalog_path)


def _count_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _bounded_values(values: list[str], *, max_items: int = MAX_WORKBOOK_SHEET_SAMPLE) -> list[str]:
    return [str(value) for value in values[:max_items]]


def _workbook_source_diagnostics(sheet_rows: list[dict[str, Any]]) -> dict[str, Any]:
    sheet_names = [str(row["sheet_name"]) for row in sheet_rows]
    included = [row for row in sheet_rows if row["status"] == "included"]
    skipped = [row for row in sheet_rows if row["status"] == "skipped"]
    bounded_rows = sheet_rows[:MAX_WORKBOOK_SHEET_SAMPLE]
    return {
        "source_kind": "workbook_strategy_catalog",
        "workbook_sheet_count": len(sheet_rows),
        "workbook_included_sheet_count": len(included),
        "workbook_skipped_sheet_count": len(skipped),
        "workbook_strategy_count": sum(int(row.get("strategy_count") or 0) for row in sheet_rows),
        "workbook_sheet_status_counts": _count_by_key(sheet_rows, "status"),
        "workbook_sheet_kind_counts": _count_by_key(sheet_rows, "sheet_kind"),
        "workbook_sheet_names": _bounded_values(sheet_names),
        "workbook_sheet_names_truncated": len(sheet_names) > MAX_WORKBOOK_SHEET_SAMPLE,
        "workbook_included_sheet_names": _bounded_values([str(row["sheet_name"]) for row in included]),
        "workbook_included_sheet_names_truncated": len(included) > MAX_WORKBOOK_SHEET_SAMPLE,
        "workbook_skipped_sheet_names": _bounded_values([str(row["sheet_name"]) for row in skipped]),
        "workbook_skipped_sheet_names_truncated": len(skipped) > MAX_WORKBOOK_SHEET_SAMPLE,
        "workbook_sheet_rows": bounded_rows,
        "workbook_sheet_rows_truncated": len(sheet_rows) > MAX_WORKBOOK_SHEET_SAMPLE,
        "workbook_fallback_limits": _xlsx_fallback_limits(),
    }


def _load_workbook_strategy_catalog_with_diagnostics(catalog_path: Path) -> tuple[list[StrategyCatalogRow], dict[str, Any]]:
    sheets = _excel_sheet_frames(catalog_path)
    if not sheets:
        raise ValueError(f"spreadsheet strategy catalog is empty: {catalog_path}")

    rows: list[StrategyCatalogRow] = []
    sheet_rows: list[dict[str, Any]] = []
    for sheet_name, frame in sheets:
        sheet_frame = _sheet_frame_with_source(frame, sheet_name)
        if _has_direct_strategy_columns(frame):
            sheet_kind = "direct_strategy_catalog"
            sheet_strategies = _strategy_rows_from_direct_frame(sheet_frame, catalog_path)
            skip_reasons: list[str] = [] if sheet_strategies else ["no_strategy_rows"]
        elif is_spreadsheet_lead_frame(frame):
            sheet_kind = "spreadsheet_lead_catalog"
            sheet_strategies = compile_spreadsheet_lead_frame(sheet_frame, source_path=catalog_path)
            skip_reasons = [] if sheet_strategies else ["no_strategy_rows"]
        else:
            sheet_kind = "unsupported_sheet"
            sheet_strategies = []
            skip_reasons = ["unsupported_sheet_columns"]
        status = "included" if sheet_strategies else "skipped"
        rows.extend(sheet_strategies)
        sheet_rows.append(
            {
                "sheet_name": str(sheet_name),
                "status": status,
                "sheet_kind": sheet_kind,
                "row_count": int(len(frame.index)),
                "column_count": int(len(frame.columns)),
                "strategy_count": len(sheet_strategies),
                "skip_reasons": skip_reasons,
            }
        )

    if not rows:
        first_missing = REQUIRED_STRATEGY_COLUMNS.difference(_canonical_strategy_catalog_frame(sheets[0][1]).columns)
        joined = ", ".join(sorted(first_missing)) if first_missing else "no strategy rows"
        raise ValueError(f"strategy workbook contained no usable sheets: {catalog_path}; first sheet missing: {joined}")
    return rows, _workbook_source_diagnostics(sheet_rows)


def load_strategy_catalog_with_diagnostics(path: str | Path) -> tuple[list[StrategyCatalogRow], dict[str, Any]]:
    catalog_path = Path(path)
    if catalog_path.is_dir():
        rows: list[StrategyCatalogRow] = []
        for child in sorted(catalog_path.iterdir()):
            if child.suffix.lower() in RECOGNIZED_STRATEGY_CATALOG_SUFFIXES:
                rows.extend(load_strategy_catalog(child))
        if not rows:
            raise ValueError(f"strategy catalog directory contained no supported files: {catalog_path}")
        return rows, {}

    if catalog_path.suffix.lower() in LEGACY_XLS_STRATEGY_CATALOG_SUFFIXES:
        _raise_unsupported_legacy_xls(catalog_path)

    if catalog_path.suffix.lower() in WORKBOOK_STRATEGY_CATALOG_SUFFIXES:
        return _load_workbook_strategy_catalog_with_diagnostics(catalog_path)

    if catalog_path.suffix.lower() == ".json":
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        compiled = compile_strategy_config_payload(payload, source_path=catalog_path)
        if compiled:
            return compiled, {}

    source_frame = _load_table(catalog_path)
    return _strategy_rows_from_table(source_frame, catalog_path), {}


def load_strategy_catalog(path: str | Path) -> list[StrategyCatalogRow]:
    rows, _diagnostics = load_strategy_catalog_with_diagnostics(path)
    return rows


def _descriptor_from_payload(payload: dict[str, Any], *, default_source_path: Path | None = None) -> VenueArchiveDescriptor:
    window_payload = payload.get("window") or {}
    if "start" not in window_payload and "start" in payload:
        window_payload = {"start": payload["start"], "end": payload["end"]}
    if "start" not in window_payload or "end" not in window_payload:
        raise ValueError("venue archive descriptor requires window.start and window.end")
    manifest_path = payload.get("manifest_path")
    if manifest_path is None and default_source_path is not None:
        manifest_path = default_source_path
    elif manifest_path is not None and default_source_path is not None:
        manifest_candidate = Path(manifest_path)
        if not manifest_candidate.is_absolute():
            manifest_path = default_source_path.parent / manifest_candidate
    data_path = payload.get("data_path")
    if data_path is not None and default_source_path is not None:
        data_candidate = Path(data_path)
        if not data_candidate.is_absolute():
            data_path = default_source_path.parent / data_candidate
    return VenueArchiveDescriptor(
        descriptor_id=str(payload["descriptor_id"]),
        venue=str(payload["venue"]),
        symbol=str(payload["symbol"]),
        data_family=str(payload.get("data_family", "mixed")),
        interval=_optional_str(payload.get("interval")),
        manifest_path=Path(manifest_path) if manifest_path else None,
        data_path=Path(data_path) if data_path else None,
        window=DataWindow(start=window_payload["start"], end=window_payload["end"]),
        source_access_mode=str(payload.get("source_access_mode", "archive_or_manifest")),
        checksum_policy=str(payload.get("checksum_policy", "required_for_strict_evidence")),
        diagnostic_only=bool(payload.get("diagnostic_only", True)),
        source_integrity=dict(payload.get("source_integrity", {}) or {}),
        notes=_parse_tags(payload.get("notes")),
    )


def load_venue_archive_descriptors(path: str | Path) -> list[VenueArchiveDescriptor]:
    descriptor_path = Path(path)
    payload = json.loads(descriptor_path.read_text(encoding="utf-8"))
    rows = payload.get("venue_archives", payload.get("descriptors", payload))
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        raise ValueError("venue archive descriptor file must contain an object or list")
    return [_descriptor_from_payload(dict(row), default_source_path=descriptor_path) for row in rows]


def load_sandbox_run_spec(path: str | Path) -> SandboxRunSpec:
    spec_path = Path(path)
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("sandbox run spec must be a JSON object")
    spec_payload = payload.get("run_template", payload)
    if not isinstance(spec_payload, dict):
        raise ValueError("sandbox run_template must be a JSON object")
    window_payload = spec_payload.get("data_window") or spec_payload.get("window")
    if not isinstance(window_payload, dict):
        raise ValueError("sandbox run spec requires data_window")
    return SandboxRunSpec(
        run_id=str(spec_payload["run_id"]),
        data_window=DataWindow(window_payload["start"], window_payload["end"]),
        validation_profile=spec_payload.get("validation_profile", "sandbox_fast"),
        holding_periods=tuple(spec_payload.get("holding_periods", (1, 2, 4, 8))),
        exit_variants=tuple(spec_payload.get("exit_variants", ({"variant_id": "fixed_hold", "exit_profile": "fixed_hold"},))),
        filter_variants=tuple(spec_payload.get("filter_variants", ({"variant_id": "base"},))),
        round_trip_cost_bps=float(spec_payload.get("round_trip_cost_bps", 8.0)),
        min_trades=int(spec_payload.get("min_trades", 5)),
        max_evidence_requests=int(spec_payload.get("max_evidence_requests", 10)),
        rank_top_n=int(spec_payload.get("rank_top_n", 100)),
        description=str(spec_payload.get("description", "")),
    )
