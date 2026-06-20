from __future__ import annotations

from io import BytesIO
import gzip
from pathlib import Path
import tarfile
import zipfile

import pytest

import tradingbotsuite.research_sandbox.market_data as market_data_module
from tradingbotsuite.research_sandbox.market_data import load_market_frame


def _csv_payload(rows: int = 2) -> bytes:
    lines = ["timestamp,open,high,low,close,volume"]
    for index in range(rows):
        day = index + 1
        close = 100 + index
        lines.append(f"2024-01-{day:02d},100,101,99,{close},10")
    return ("\n".join(lines) + "\n").encode("utf-8")


def test_zip_member_size_limit_blocks_before_market_normalization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    zip_path = tmp_path / "oversized.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("market.csv", _csv_payload(rows=3))

    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_SELECTED_MEMBERS", 4)
    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_MEMBER_BYTES", 32)
    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_SELECTED_TOTAL_BYTES", 1024)

    with pytest.raises(ValueError, match="container_member_bytes_limit_exceeded"):
        load_market_frame(zip_path)


def test_zip_gzip_member_decompression_limit_blocks_expanded_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    zip_path = tmp_path / "expanded-gzip.zip"
    compressed_payload = gzip.compress(_csv_payload(rows=4))
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("market.csv.gz", compressed_payload)

    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_SELECTED_MEMBERS", 4)
    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_MEMBER_BYTES", 1024)
    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_SELECTED_TOTAL_BYTES", 2048)
    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_GZIP_DECOMPRESSED_BYTES", 32)

    with pytest.raises(ValueError, match="container_member_decompressed_bytes_limit_exceeded"):
        load_market_frame(zip_path)


def test_tar_selected_member_count_limit_blocks_multi_member_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tar_path = tmp_path / "too-many-members.tar"
    with tarfile.open(tar_path, "w") as archive:
        for name in ("market-a.csv", "market-b.csv"):
            payload = _csv_payload(rows=1)
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, BytesIO(payload))

    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_SELECTED_MEMBERS", 1)

    with pytest.raises(ValueError, match="container_selected_member_count_limit_exceeded"):
        load_market_frame(tar_path)


def test_accepted_zip_container_records_loader_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    zip_path = tmp_path / "bounded.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("market.csv", _csv_payload(rows=2))

    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_SELECTED_MEMBERS", 4)
    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_MEMBER_BYTES", 1024)
    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_SELECTED_TOTAL_BYTES", 2048)
    monkeypatch.setattr(market_data_module, "MAX_CONTAINER_GZIP_DECOMPRESSED_BYTES", 4096)

    frame = load_market_frame(zip_path)

    metadata = frame.attrs["sandbox_normalization_metadata"]["container_member_metadata"]
    assert metadata["container_kind"] == "zip"
    assert metadata["selected_member_count"] == 1
    assert metadata["selected_member_declared_byte_count"] == 1
    assert metadata["selected_member_declared_byte_total"] == len(_csv_payload(rows=2))
    assert metadata["container_loader_limits"] == {
        "max_selected_members": 4,
        "max_member_bytes": 1024,
        "max_selected_total_bytes": 2048,
        "max_gzip_decompressed_bytes": 4096,
    }
