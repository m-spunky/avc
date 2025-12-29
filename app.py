import os
import json
import shutil
import asyncio
import subprocess
from typing import List, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time

# Import analysis pipeline (to be implemented)
from analysis.pipeline import run_analysis_pipeline

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
STORAGE_DIR = "storage"
STATIC_DIR = "static"
SCENARIOS_DIR = os.path.join(STORAGE_DIR, "scenarios")
SCENARIO_SESSIONS_DIR = os.path.join(STORAGE_DIR, "scenario_sessions")

# In-memory session store
# { session_id: { "clients": [WebSocket], "participants": [id1, id2] } }
sessions: Dict[str, Dict] = {}

# Ensure storage directories exist
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(SCENARIOS_DIR, exist_ok=True)
os.makedirs(SCENARIO_SESSIONS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

@app.get("/")
async def get_home():
    return FileResponse(f"{STATIC_DIR}/index.html")

@app.get("/call/{session_id}")
async def get_call_page(session_id: str):
    return FileResponse(f"{STATIC_DIR}/call.html")

@app.get("/report/{session_id}")
async def get_report_page(session_id: str):
    # Check if report exists
    report_path = os.path.join(STORAGE_DIR, session_id, "report", "report.json")
    if os.path.exists(report_path):
        return FileResponse(f"{STATIC_DIR}/report.html")
    else:
        # If no report, maybe show a "processing" page or just the report page which handles pending state
        return FileResponse(f"{STATIC_DIR}/report.html")

# --- WebSocket Signaling ---

class ConnectionManager:
    def __init__(self):
        # session_id -> list of WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        
        if len(self.active_connections[session_id]) >= 2:
            await websocket.close(code=4000, reason="Session full")
            return False
            
        self.active_connections[session_id].append(websocket)
        return True

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, message: str, session_id: str, sender: WebSocket):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                if connection != sender:
                    await connection.send_text(message)

    async def broadcast_to_all(self, message: str, session_id: str):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    success = await manager.connect(websocket, session_id)
    if not success:
        return

    try:
        while True:
            data = await websocket.receive_text()
            # Relay message to other peer
            await manager.broadcast(data, session_id, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        # Notify others?
        # await manager.broadcast(json.dumps({"type": "peer-left"}), session_id, None)

# --- Media Upload & Processing ---

@app.post("/create_session")
async def create_session():
    import uuid
    session_id = str(uuid.uuid4())[:8] # Short ID
    session_path = os.path.join(STORAGE_DIR, session_id)
    os.makedirs(os.path.join(session_path, "raw"), exist_ok=True)
    os.makedirs(os.path.join(session_path, "merged"), exist_ok=True)
    os.makedirs(os.path.join(session_path, "audio"), exist_ok=True)
    os.makedirs(os.path.join(session_path, "report"), exist_ok=True)
    
    # Init metadata
    metadata = {
        "session_id": session_id,
        "created_at": time.time(),
        "status": "created"
    }
    with open(os.path.join(session_path, "metadata.json"), "w") as f:
        json.dump(metadata, f)
        
    return {"session_id": session_id}

@app.post("/upload/{session_id}/{participant_id}")
async def upload_chunk(session_id: str, participant_id: str, file: UploadFile = File(...), chunk_index: int = Form(...)):
    session_path = os.path.join(STORAGE_DIR, session_id)
    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Append chunk to a raw file
    raw_path = os.path.join(session_path, "raw")
    filename = f"{participant_id}.webm" 
    file_path = os.path.join(raw_path, filename)
    
    # Append mode
    with open(file_path, "ab") as f:
        shutil.copyfileobj(file.file, f)
        
    return {"status": "chunk_received", "size": os.path.getsize(file_path)}

@app.post("/end_call/{session_id}")
async def end_call(session_id: str, background_tasks: BackgroundTasks):
    session_path = os.path.join(STORAGE_DIR, session_id)
    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update status
    meta_path = os.path.join(session_path, "metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            data = json.load(f)
        data["status"] = "processing"
        data["end_time"] = time.time()
        with open(meta_path, "w") as f:
            json.dump(data, f)

    # Notify all participants to redirect to report page
    await manager.broadcast_to_all(json.dumps({"type": "session-ended"}), session_id)

    # Trigger analysis in background
    background_tasks.add_task(run_analysis_pipeline, session_id)
    
    return {"status": "processing_started"}

@app.get("/api/report/{session_id}")
async def get_report_data(session_id: str):
    report_path = os.path.join(STORAGE_DIR, session_id, "report", "report.json")
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            return json.load(f)
    else:
        # Check if processing
        meta_path = os.path.join(STORAGE_DIR, session_id, "metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
            if meta.get("status") == "processing":
                return JSONResponse(status_code=202, content={"status": "processing"})
        
        return JSONResponse(status_code=404, content={"status": "not_found"})

@app.post("/api/analyze_video")
async def analyze_video_endpoint(request: dict):
    """
    Trigger analysis for a given session/video ID.
    Input: {"session_id": "xxx"} or {"video_id": "xxx"}
    Returns: Analysis report JSON
    """
    session_id = request.get("session_id") or request.get("video_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id or video_id required")
    
    session_path = os.path.join(STORAGE_DIR, session_id)
    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if raw files exist
    raw_files = os.listdir(os.path.join(session_path, "raw"))
    if not raw_files:
        raise HTTPException(status_code=400, detail="No video files found for this session")
    
    # Run analysis synchronously (blocking)
    try:
        run_analysis_pipeline(session_id)
        
        # Return the report
        report_path = os.path.join(session_path, "report", "report.json")
        if os.path.exists(report_path):
            with open(report_path, "r") as f:
                return json.load(f)
        else:
            raise HTTPException(status_code=500, detail="Analysis completed but report not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# --- Scenario-Based AVC Endpoints ---

@app.get("/api/scenarios")
async def list_scenarios():
    """
    List all available scenario videos
    """
    scenarios = []
    
    if not os.path.exists(SCENARIOS_DIR):
        return {"scenarios": []}
    
    for scenario_id in os.listdir(SCENARIOS_DIR):
        scenario_path = os.path.join(SCENARIOS_DIR, scenario_id)
        metadata_file = os.path.join(scenario_path, "metadata.json")
        
        if os.path.isdir(scenario_path) and os.path.exists(metadata_file):
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
                scenarios.append(metadata)
    
    return {"scenarios": scenarios}


@app.get("/api/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    """
    Get details of a specific scenario
    """
    scenario_path = os.path.join(SCENARIOS_DIR, scenario_id)
    metadata_file = os.path.join(scenario_path, "metadata.json")
    
    if not os.path.exists(metadata_file):
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    with open(metadata_file, "r") as f:
        metadata = json.load(f)
    
    return metadata


@app.post("/api/scenarios")
async def create_scenario(
    title: str = Form(...),
    description: str = Form(...),
    steps: str = Form(...),  # JSON string
    video: UploadFile = File(...)
):
    """
    Upload a new scenario video (admin endpoint)
    """
    import uuid
    scenario_id = f"scenario_{str(uuid.uuid4())[:8]}"
    scenario_path = os.path.join(SCENARIOS_DIR, scenario_id)
    os.makedirs(scenario_path, exist_ok=True)
    
    # Save video file
    video_path = os.path.join(scenario_path, "video.mp4")
    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)
    
    # Get video duration using OpenCV
    import cv2
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    cap.release()
    
    # Parse steps
    steps_data = json.loads(steps)
    
    # Create metadata
    metadata = {
        "id": scenario_id,
        "title": title,
        "description": description,
        "video_path": f"/storage/scenarios/{scenario_id}/video.mp4",
        "duration": round(duration, 2),
        "steps": steps_data,
        "created_at": time.time()
    }
    
    with open(os.path.join(scenario_path, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    return metadata


@app.post("/api/scenario/start")
async def start_scenario_session(request: dict):
    """
    Start a new scenario practice session
    """
    scenario_id = request.get("scenario_id")
    
    if not scenario_id:
        raise HTTPException(status_code=400, detail="scenario_id required")
    
    # Verify scenario exists
    scenario_path = os.path.join(SCENARIOS_DIR, scenario_id)
    if not os.path.exists(scenario_path):
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # Create session
    import uuid
    session_id = str(uuid.uuid4())[:8]
    session_path = os.path.join(SCENARIO_SESSIONS_DIR, session_id)
    os.makedirs(os.path.join(session_path, "raw"), exist_ok=True)
    os.makedirs(os.path.join(session_path, "merged"), exist_ok=True)
    os.makedirs(os.path.join(session_path, "audio"), exist_ok=True)
    os.makedirs(os.path.join(session_path, "report"), exist_ok=True)
    
    # Create session metadata
    metadata = {
        "session_id": session_id,
        "session_type": "scenario",
        "scenario_id": scenario_id,
        "created_at": time.time(),
        "status": "recording"
    }
    
    with open(os.path.join(session_path, "metadata.json"), "w") as f:
        json.dump(metadata, f)
    
    return {"session_id": session_id, "scenario_id": scenario_id}


@app.post("/api/scenario/upload/{session_id}")
async def upload_scenario_recording(
    session_id: str,
    file: UploadFile = File(...),
    chunk_index: int = Form(...)
):
    """
    Upload user recording chunks during scenario session
    """
    session_path = os.path.join(SCENARIO_SESSIONS_DIR, session_id)
    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Append chunk to user recording
    raw_path = os.path.join(session_path, "raw")
    filename = "user.webm"
    file_path = os.path.join(raw_path, filename)
    
    with open(file_path, "ab") as f:
        shutil.copyfileobj(file.file, f)
    
    return {"status": "chunk_received", "size": os.path.getsize(file_path)}


@app.post("/api/scenario/end/{session_id}")
async def end_scenario_session(session_id: str, background_tasks: BackgroundTasks):
    """
    End scenario session and trigger analysis
    """
    session_path = os.path.join(SCENARIO_SESSIONS_DIR, session_id)
    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update status
    meta_path = os.path.join(session_path, "metadata.json")
    with open(meta_path, "r") as f:
        data = json.load(f)
    
    data["status"] = "processing"
    data["end_time"] = time.time()
    
    with open(meta_path, "w") as f:
        json.dump(data, f)
    
    # Trigger analysis in background
    background_tasks.add_task(run_scenario_analysis, session_id)
    
    return {"status": "processing_started"}


@app.get("/api/scenario/report/{session_id}")
async def get_scenario_report(session_id: str):
    """
    Get step-wise analysis report for scenario session
    """
    report_path = os.path.join(SCENARIO_SESSIONS_DIR, session_id, "report", "report.json")
    
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            return json.load(f)
    else:
        # Check if processing
        meta_path = os.path.join(SCENARIO_SESSIONS_DIR, session_id, "metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
            if meta.get("status") == "processing":
                return JSONResponse(status_code=202, content={"status": "processing"})
        
        return JSONResponse(status_code=404, content={"status": "not_found"})


@app.get("/scenario")
async def get_scenario_page():
    """Scenario selection page"""
    return FileResponse(f"{STATIC_DIR}/scenario.html")


@app.get("/practice/{session_id}")
async def get_practice_page(session_id: str):
    """Scenario practice page"""
    return FileResponse(f"{STATIC_DIR}/practice.html")


@app.get("/scenario_report/{session_id}")
async def get_scenario_report_page(session_id: str):
    """Scenario report page"""
    return FileResponse(f"{STATIC_DIR}/scenario_report.html")


def run_scenario_analysis(session_id: str):
    """
    Run analysis pipeline for scenario session
    """
    print(f"Starting scenario analysis for session: {session_id}")
    session_path = os.path.join(SCENARIO_SESSIONS_DIR, session_id)
    
    try:
        # Load session metadata
        with open(os.path.join(session_path, "metadata.json"), "r") as f:
            session_meta = json.load(f)
        
        scenario_id = session_meta.get("scenario_id")
        
        # Load scenario metadata
        scenario_path = os.path.join(SCENARIOS_DIR, scenario_id)
        with open(os.path.join(scenario_path, "metadata.json"), "r") as f:
            scenario_meta = json.load(f)
        
        # Process user recording (no merging needed, just one video)
        raw_file = os.path.join(session_path, "raw", "user.webm")
        
        if not os.path.exists(raw_file):
            print("No user recording found")
            return
        
        # Convert to mp4 and extract audio
        merged_video = os.path.join(session_path, "merged", "user_session.mp4")
        merged_audio = os.path.join(session_path, "audio", "user_audio.wav")
        
        # Convert video
        subprocess.run([
            "ffmpeg", "-y", "-i", raw_file,
            "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
            merged_video
        ], check=True)
        
        # Extract audio
        subprocess.run([
            "ffmpeg", "-y", "-i", merged_video,
            "-ac", "1", "-ar", "16000",
            merged_audio
        ], check=True)
        
        # Run comprehensive analysis
        from analysis.pipeline import run_analysis_pipeline
        
        # Temporarily change working directory context for pipeline
        import sys
        original_path = os.getcwd()
        
        # Create a wrapper to use scenario_sessions path
        class ScenarioAnalysisPipeline:
            @staticmethod
            def run(session_id):
                # Modify storage path temporarily
                temp_storage = os.path.join(original_path, SCENARIO_SESSIONS_DIR)
                
                # Import and run analysis modules directly
                from analysis.session_metadata import extract_session_metadata
                from analysis.audio_analysis import analyze_audio
                from analysis.transcript_analysis import analyze_transcript
                from analysis.video_analysis import analyze_video
                
                session_rel_path = os.path.join(temp_storage, session_id)
                
                # Get video duration
                import cv2
                cap = cv2.VideoCapture(merged_video)
                fps = cap.get(cv2.CAP_PROP_FPS)
                # Calculate duration from actual frames
                frame_count = 0
                while cap.isOpened():
                    ret, _ = cap.read()
                    if not ret:
                        break
                    frame_count += 1
                video_duration = frame_count / fps if fps > 0 else 0
                cap.release()
                
                # Session metadata
                session_metadata = extract_session_metadata(session_id, session_rel_path, video_duration)
                session_metadata["session_type"] = "scenario"
                session_metadata["scenario_id"] = scenario_id
                
                # Audio analysis
                audio_results = analyze_audio(merged_audio)
                
                # Transcript analysis
                transcript_results = analyze_transcript(
                    audio_results.get("transcript", ""),
                    audio_results.get("segments", []),
                    audio_results.get("word_count", 0),
                    audio_results.get("filler_count", 0)
                )
                
                # Video analysis
                video_results = {"user": analyze_video(merged_video)}
                
                # Generate report with step-wise breakdown
                from analysis.pipeline import generate_comprehensive_report
                report = generate_comprehensive_report(
                    session_id,
                    session_metadata,
                    audio_results,
                    transcript_results,
                    video_results
                )
                
                # Add step-wise analysis
                report["stepwise_analysis"] = generate_stepwise_metrics(
                    report,
                    scenario_meta.get("steps", [])
                )
                
                # Save report
                report_path = os.path.join(session_rel_path, "report", "report.json")
                with open(report_path, "w") as f:
                    json.dump(report, f, indent=2)
                
                # Update metadata
                meta_path = os.path.join(session_rel_path, "metadata.json")
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                meta["status"] = "completed"
                with open(meta_path, "w") as f:
                    json.dump(meta, f)
                
                print(f"Scenario analysis completed for session: {session_id}")
        
        ScenarioAnalysisPipeline.run(session_id)
        
    except Exception as e:
        print(f"Scenario analysis failed: {e}")
        import traceback
        traceback.print_exc()


def generate_stepwise_metrics(report, steps):
    """
    Generate step-wise breakdown of metrics
    """
    stepwise = []
    
    for i, step in enumerate(steps):
        step_start = step.get("time", 0)
        step_end = steps[i + 1].get("time", 999999) if i + 1 < len(steps) else 999999
        
        # Extract metrics for this time range
        step_metrics = {
            "step": step,
            "time_range": {"start": step_start, "end": step_end},
            "metrics": extract_metrics_for_timerange(report, step_start, step_end)
        }
        
        stepwise.append(step_metrics)
    
    return stepwise


def extract_metrics_for_timerange(report, start_time, end_time):
    """
    Extract analysis metrics for a specific time range
    """
    # Filter video emotions by time range
    video_data = report.get("video_analysis", {}).get("participants", {})
    filtered_emotions = []
    
    for participant_id, participant_data in video_data.items():
        emotions = participant_data.get("emotions", [])
        for emotion_entry in emotions:
            if start_time <= emotion_entry.get("time", 0) < end_time:
                filtered_emotions.append(emotion_entry)
    
    # Calculate emotion distribution for this step
    emotion_counts = {}
    for emotion_entry in filtered_emotions:
        emotion = emotion_entry.get("emotion")
        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
    
    total = sum(emotion_counts.values())
    emotion_distribution = {}
    if total > 0:
        for emotion, count in emotion_counts.items():
            emotion_distribution[emotion] = round((count / total) * 100, 2)
    
    # Return step-specific metrics
    return {
        "emotion_distribution": emotion_distribution,
        "dominant_emotion": max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else "neutral",
        "sample_count": len(filtered_emotions)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

