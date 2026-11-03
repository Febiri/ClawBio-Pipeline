import os
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.orchestrator import run_orchestration


app = FastAPI(
    title="ClawBio-Pipeline Cloud & REST API",
    description="Automated Bioinformatics Workflow Orchestrator with Cloud S3 and Anomaly Flagging",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job repository (can be backed by Redis / DB in production)
JOBS_DB: Dict[str, Dict[str, Any]] = {}


class SampleInput(BaseModel):
    sample_id: str
    raw_fastq: str


class PipelineRunRequest(BaseModel):
    project_name: Optional[str] = "Bioinformatics Cloud Pipeline"
    execution_mode: Optional[str] = "simulation"
    reference_genome: Optional[str] = "hg38"
    max_workers: Optional[int] = 4
    samples: List[SampleInput]
    s3_output_uri: Optional[str] = None
    qc_thresholds: Optional[Dict[str, float]] = None


def execute_pipeline_task(job_id: str, run_config: Dict[str, Any]):
    """Background task executor for pipeline runs."""
    JOBS_DB[job_id]["status"] = "RUNNING"
    JOBS_DB[job_id]["started_at"] = datetime.datetime.utcnow().isoformat()

    try:
        results = run_orchestration(
            config=run_config,
            mode=run_config.get("execution_mode", "simulation"),
            max_workers=run_config.get("max_workers", 4),
        )

        JOBS_DB[job_id]["status"] = "COMPLETED"
        JOBS_DB[job_id]["completed_at"] = datetime.datetime.utcnow().isoformat()
        JOBS_DB[job_id]["report_path"] = results["report_path"]
        JOBS_DB[job_id]["flagged_count"] = results["flagged_count"]
        JOBS_DB[job_id]["total_samples"] = results["total_samples"]
        JOBS_DB[job_id]["anomalies"] = results["anomalies"]

        # Keep a sanitized summary of metrics
        if "metrics_df" in results:
            df = results["metrics_df"]
            # Exclude large series if needed, keep json serializable records
            summary_cols = [
                c
                for c in [
                    "sample_id",
                    "execution_mode",
                    "mapped_percentage",
                    "gc_content_percent",
                    "mean_phred_quality",
                    "status_label",
                    "execution_time_sec",
                    "peak_ram_mb",
                ]
                if c in df.columns
            ]
            JOBS_DB[job_id]["metrics_summary"] = df[summary_cols].to_dict(orient="records")

    except Exception as e:
        JOBS_DB[job_id]["status"] = "FAILED"
        JOBS_DB[job_id]["completed_at"] = datetime.datetime.utcnow().isoformat()
        JOBS_DB[job_id]["error"] = str(e)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ClawBio-Pipeline API",
        "version": "2.0.0",
        "active_jobs": len(JOBS_DB),
    }


@app.post("/api/pipeline/run-async")
def trigger_pipeline_async(request: PipelineRunRequest, background_tasks: BackgroundTasks):
    """Triggers an asynchronous pipeline orchestration job with S3 / local samples."""
    job_id = str(uuid.uuid4())
    run_config = request.model_dump() if hasattr(request, "model_dump") else request.dict()

    JOBS_DB[job_id] = {
        "job_id": job_id,
        "status": "PENDING",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "project_name": request.project_name,
        "execution_mode": request.execution_mode,
        "total_samples": len(request.samples),
        "report_path": None,
        "error": None,
    }

    background_tasks.add_task(execute_pipeline_task, job_id, run_config)

    return {
        "job_id": job_id,
        "status": "PENDING",
        "message": f"Pipeline job {job_id} scheduled for {len(request.samples)} sample(s).",
    }


@app.post("/api/pipeline/upload-and-run")
async def upload_fastq_and_run(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    sample_id: Optional[str] = Form(None),
    mode: Optional[str] = Form("simulation"),
    project_name: Optional[str] = Form("Direct Upload Study"),
):
    """Uploads a raw FASTQ file and queues asynchronous pipeline execution."""
    job_id = str(uuid.uuid4())
    assigned_sample_id = sample_id or Path(file.filename).stem or f"Upload_{job_id[:8]}"

    upload_dir = Path("data") / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = upload_dir / f"{job_id}_{file.filename}"

    with open(saved_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    run_config = {
        "project_name": project_name,
        "execution_mode": mode,
        "reference_genome": "hg38",
        "samples": [{"sample_id": assigned_sample_id, "raw_fastq": str(saved_path)}],
        "output_dir": "results",
    }

    JOBS_DB[job_id] = {
        "job_id": job_id,
        "status": "PENDING",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "project_name": project_name,
        "execution_mode": mode,
        "total_samples": 1,
        "report_path": None,
        "error": None,
    }

    background_tasks.add_task(execute_pipeline_task, job_id, run_config)

    return {
        "job_id": job_id,
        "sample_id": assigned_sample_id,
        "status": "PENDING",
        "message": f"Uploaded FASTQ '{file.filename}' and queued job {job_id}.",
    }


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    """Retrieves status, metrics, and anomaly flags for a submitted job."""
    if job_id not in JOBS_DB:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return JOBS_DB[job_id]


@app.get("/api/jobs/{job_id}/report")
def download_job_report(job_id: str):
    """Downloads or renders the Plotly HTML report generated for a specific job."""
    if job_id not in JOBS_DB:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    job = JOBS_DB[job_id]
    if job["status"] != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=f"Report not available. Job status is currently '{job['status']}'.",
        )

    report_path = job.get("report_path")
    if not report_path or not Path(report_path).exists():
        raise HTTPException(status_code=404, detail="HTML report file missing on disk.")

    return FileResponse(
        path=report_path,
        media_type="text/html",
        filename=f"pipeline_report_{job_id[:8]}.html",
    )


@app.get("/api/jobs")
def list_jobs():
    """Lists all pipeline jobs and statuses."""
    return list(JOBS_DB.values())
