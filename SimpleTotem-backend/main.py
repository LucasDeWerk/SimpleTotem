import multiprocessing
import sys
import uvicorn

if __name__ == "__main__":
    multiprocessing.freeze_support()

    if "--sitef-worker" in sys.argv:
        from services.sitef_worker import main as worker_main
        sys.exit(worker_main())

    from app import app as application
    uvicorn.run(application, host="127.0.0.1", port=8000, reload=False)
