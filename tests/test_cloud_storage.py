import pytest
from unittest.mock import MagicMock
from pathlib import Path
from src.cloud_storage import (
    is_s3_uri,
    parse_s3_uri,
    download_s3_file,
    upload_s3_file,
)


def test_is_s3_uri():
    assert is_s3_uri("s3://my-bucket/sample.fastq") is True
    assert is_s3_uri("s3://bucket") is True
    assert is_s3_uri("https://s3.amazonaws.com/bucket") is False
    assert is_s3_uri("data/raw/sample.fastq") is False
    assert is_s3_uri(None) is False


def test_parse_s3_uri():
    bucket, key = parse_s3_uri("s3://genomics-vault/cohort-1/Tumor_A.fastq")
    assert bucket == "genomics-vault"
    assert key == "cohort-1/Tumor_A.fastq"

    with pytest.raises(ValueError):
        parse_s3_uri("not-an-s3-uri")

    with pytest.raises(ValueError):
        parse_s3_uri("s3://")


def test_download_s3_file(tmp_path):
    mock_s3 = MagicMock()
    dest = tmp_path / "downloaded.fastq"

    # Define mock behavior: create an empty file when download_file is called
    def fake_download(bucket, key, filename):
        Path(filename).write_text("@MOCK_SEQ\nACGT\n+\nIIII\n", encoding="utf-8")

    mock_s3.download_file.side_effect = fake_download

    result = download_s3_file("s3://test-bucket/sample.fastq", local_dest=dest, s3_client=mock_s3)
    assert result.exists()
    mock_s3.download_file.assert_called_once_with("test-bucket", "sample.fastq", str(dest))


def test_upload_s3_file(tmp_path):
    mock_s3 = MagicMock()
    test_file = tmp_path / "report.html"
    test_file.write_text("<h1>Report</h1>", encoding="utf-8")

    result_uri = upload_s3_file(test_file, "s3://reports-bucket/study/report.html", s3_client=mock_s3)
    assert result_uri == "s3://reports-bucket/study/report.html"
    mock_s3.upload_file.assert_called_once_with(
        str(test_file), "reports-bucket", "study/report.html"
    )

