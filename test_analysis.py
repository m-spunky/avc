import asyncio
from analysis.pipeline import run_analysis_pipeline
import sys

# Usage: python test_analysis.py <session_id>
if __name__ == "__main__":
    session_id = "28eb59ba"
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
    
    print(f"Manually triggering analysis for {session_id}")
    run_analysis_pipeline(session_id)
