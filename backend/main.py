# SERPERIOR/run_api.py

import uvicorn
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    uvicorn.run(
        "serperior.api.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )