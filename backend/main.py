"""Backend entry point. Run with:

    conda activate xpu_env_n
    cd backend
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload

The local OpenVINO model server should already be running on port 8000.
"""

from api.app import app  # noqa: F401 — import triggers route registration

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
