"""
Session Metadata Module
Extracts and formats session-level metadata
"""

import os
import json
from datetime import datetime
from typing import Dict, Any


def extract_session_metadata(session_id: str, session_path: str, video_duration: float) -> Dict[str, Any]:
    """
    Extract session metadata from session files
    
    Args:
        session_id: Unique session identifier
        session_path: Path to session directory
        video_duration: Duration of video in seconds
        
    Returns:
        Dictionary with session metadata
    """
    
    metadata_file = os.path.join(session_path, "metadata.json")
    
    # Load existing metadata if available
    metadata = {}
    if os.path.exists(metadata_file):
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
    
    # Determine session type
    session_type = determine_session_type(session_path)
    
    # Get session date
    created_at = metadata.get("created_at", datetime.now().timestamp())
    session_date = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
    
    # Format duration
    duration_formatted = format_duration(video_duration)
    
    return {
        "session_id": session_id,
        "session_type": session_type,
        "session_date": session_date,
        "session_duration": duration_formatted,
        "session_duration_seconds": round(video_duration, 2)
    }


def determine_session_type(session_path: str) -> str:
    """
    Determine if session was simulation or therapist-led
    Based on number of participants
    """
    
    raw_path = os.path.join(session_path, "raw")
    if not os.path.exists(raw_path):
        return "unknown"
    
    # Count video files
    video_files = [f for f in os.listdir(raw_path) if f.endswith(('.webm', '.mp4'))]
    
    if len(video_files) >= 2:
        return "therapist-led"
    elif len(video_files) == 1:
        return "simulation"
    else:
        return "unknown"


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format
    """
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
