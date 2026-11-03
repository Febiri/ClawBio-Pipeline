from fastapi.testclient import TestClient
from pathlib import Path
from src.api import app, JOBS_DB, execute_pipeline_task


client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ClawBio-Pipeline API"


def test_api_run_async_and_poll(tmp_path):
    fastq_file = tmp_path / "sample.fastq"
    fastq_file.write_text("@R1\nACGT\n+\nIIII\n", encoding="utf-8")

    payload = {
        "project_name": "API Test Project",
        "execution_mode": "simulation",
        "max_workers": 2,
        "samples": [{"sample_id": "API_Sample", "raw_fastq": str(fastq_file)}],
    }

    # Trigger job
    post_res = client.post("/api/pipeline/run-async", json=payload)
    assert post_res.status_code == 200
    res_data = post_res.json()
    assert "job_id" in res_data
    assert res_data["status"] == "PENDING"
    job_id = res_data["job_id"]

    # Execute task synchronously for testing assertion
    execute_pipeline_task(job_id, payload)

    # Check status
    get_res = client.get(f"/api/jobs/{job_id}")
    assert get_res.status_code == 200
    job_info = get_res.json()
    assert job_info["status"] == "COMPLETED"
    assert job_info["total_samples"] == 1
    assert "report_path" in job_info

    # Download report
    report_res = client.get(f"/api/jobs/{job_id}/report")
    assert report_res.status_code == 200
    assert "text/html" in report_res.headers["content-type"]
    assert "API Test Project" in report_res.text


def test_api_upload_and_run(tmp_path):
    fastq_content = b"@READ_UPLOAD\nAGCTAGCT\n+\nIIIIIIII\n"

    response = client.post(
        "/api/pipeline/upload-and-run",
        files={"file": ("upload_test.fastq", fastq_content, "text/plain")},
        data={"sample_id": "Uploaded_Sample_1", "mode": "simulation"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["sample_id"] == "Uploaded_Sample_1"
    assert data["status"] == "PENDING"


def test_api_job_not_found():
    res = client.get("/api/jobs/invalid-job-id-999")
    assert res.status_code == 404

