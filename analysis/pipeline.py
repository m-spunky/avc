import os
import subprocess
import glob
import json
import time

def run_ffmpeg_merge(session_path: str, participants: list):
    """
    Merges participant videos side-by-side.
    Extracts audio for analysis.
    """
    # Outputs
    merged_video = os.path.join(session_path, "merged", "full_session.mp4")
    merged_audio = os.path.join(session_path, "audio", "full_audio.wav") # for transcription
    
    # Inputs
    inputs = []
    filter_complex = ""
    
    # Check what files we have
    raw_files = glob.glob(os.path.join(session_path, "raw", "*.webm"))
    if not raw_files:
        print("No raw files found.")
        return None, None

    # Construct FFmpeg command
    cmd_base = ["ffmpeg", "-y"]
    
    for i, f in enumerate(raw_files):
        cmd_base.extend(["-i", f])
        
    # Side-by-side filter
    if len(raw_files) == 2:
        filter_complex = "[0:v][1:v]hstack=inputs=2[v];[0:a][1:a]amerge=inputs=2[a]"
        cmd_base.extend(["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"])
    elif len(raw_files) == 1:
        # Just copy if only one
        cmd_base = ["ffmpeg", "-y", "-i", raw_files[0]]
    else:
        # >2 ? Just take first two or failing
        pass

    # Video output
    # We need to re-encode for compatibility usually
    cmd_base.extend(["-c:v", "libx264", "-crf", "23", "-preset", "veryfast", merged_video])
    
    print(f"Running FFmpeg merge: {' '.join(cmd_base)}")
    subprocess.run(cmd_base, check=True)

    # Audio extraction (mixdown to mono for whisper?)
    # Whisper handles stereo but mono is safer/smaller
    cmd_audio = ["ffmpeg", "-y", "-i", merged_video, "-ac", "1", "-ar", "16000", merged_audio]
    print(f"Running FFmpeg audio extract: {' '.join(cmd_audio)}")
    subprocess.run(cmd_audio, check=True)
    
    return merged_video, merged_audio

def run_analysis_pipeline(session_id: str):
    print(f"Starting comprehensive analysis for session: {session_id}")
    session_path = os.path.join("storage", session_id)
    
    try:
        # 1. FFmpeg Processing
        merged_video, merged_audio = run_ffmpeg_merge(session_path, [])
        
        if not merged_video:
            print("FFmpeg failed or no files.")
            return

        # Get video duration for metadata
        import cv2
        cap = cv2.VideoCapture(merged_video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration = frame_count / fps if fps else 0
        cap.release()

        # 2. Session Metadata Extraction
        print("Extracting session metadata...")
        from analysis.session_metadata import extract_session_metadata
        session_metadata = extract_session_metadata(session_id, session_path, video_duration)
        print("Session metadata extracted.")

        # 3. Audio Analysis (Whisper + Acoustic Features)
        print("Starting Audio Analysis (Whisper + Acoustic Features)...")
        from analysis.audio_analysis import analyze_audio
        audio_results = analyze_audio(merged_audio)
        print("Audio Analysis completed.")
        
        # 4. Transcript Analysis (OpenRouter LLM)
        print("Starting Transcript Analysis (LLM-powered)...")
        from analysis.transcript_analysis import analyze_transcript
        transcript_results = analyze_transcript(
            audio_results.get("transcript", ""),
            audio_results.get("segments", []),
            audio_results.get("word_count", 0),
            audio_results.get("filler_count", 0)
        )
        print("Transcript Analysis completed.")
        
        # 5. Video Analysis (DeepFace + Behavioral Metrics)
        # Analyzing individual raw files for per-person data
        raw_files = glob.glob(os.path.join(session_path, "raw", "*.webm"))
        video_results = {}
        
        from analysis.video_analysis import analyze_video
        for raw_file in raw_files:
            pid = os.path.basename(raw_file).split('.')[0]
            print(f"Starting Video Analysis for participant {pid}...")
            video_results[pid] = analyze_video(raw_file)
            print(f"Video Analysis for participant {pid} completed.")

        # 6. Generate Comprehensive Report
        report = generate_comprehensive_report(
            session_id,
            session_metadata,
            audio_results,
            transcript_results,
            video_results
        )
        
        report_path = os.path.join(session_path, "report", "report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
            
        # Update metadata status
        meta_path = os.path.join(session_path, "metadata.json")
        with open(meta_path, "r") as f:
            meta = json.load(f)
        meta["status"] = "completed"
        with open(meta_path, "w") as f:
            json.dump(meta, f)
            
        print(f"Comprehensive analysis completed for session: {session_id}")

    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        # Log error to metadata


def generate_comprehensive_report(session_id, session_metadata, audio_results, transcript_results, video_results):
    """
    Generate comprehensive report with all 32+ attributes
    """
    
    # Aggregate video metrics from all participants
    aggregated_video = aggregate_video_metrics(video_results)
    
    report = {
        # 🧾 A. SESSION METADATA
        "session_metadata": {
            "session_id": session_metadata["session_id"],
            "session_type": session_metadata["session_type"],
            "session_date": session_metadata["session_date"],
            "session_duration": session_metadata["session_duration"],
            "session_duration_seconds": session_metadata["session_duration_seconds"]
        },
        
        # 🎥 B. VIDEO ANALYSIS
        "video_analysis": {
            "dominant_emotion_distribution": aggregated_video.get("dominant_emotion_distribution", {}),
            "facial_emotional_variability": aggregated_video.get("facial_emotional_variability", 0),
            "facial_tension_index": aggregated_video.get("facial_tension_index", 0),
            "eye_contact_consistency": aggregated_video.get("eye_contact_consistency", 0),
            "head_movement_patterns": aggregated_video.get("head_movement_patterns", {}),
            "facial_expressiveness_score": aggregated_video.get("facial_expressiveness_score", 0),
            "stress_expression_frequency": aggregated_video.get("stress_expression_frequency", 0),
            
            # Per-participant detailed data
            "participants": video_results
        },
        
        # 🎙 C. AUDIO ANALYSIS
        "audio_analysis": {
            "speech_rate_wpm": audio_results.get("speech_rate_wpm", 0),
            "pitch_variability": audio_results.get("pitch_variability", 0),
            "volume_stability": audio_results.get("volume_stability", 0),
            "pause_frequency": audio_results.get("pause_frequency", 0),
            "average_pause_duration": audio_results.get("average_pause_duration", 0),
            "voice_stress_indicator": audio_results.get("voice_stress_indicator", 0),
            "vocal_tremor_detected": audio_results.get("vocal_tremor_detected", False),
            "speech_fluency_score": audio_results.get("speech_fluency_score", 0),
            
            # Raw data
            "transcript": audio_results.get("transcript", ""),
            "word_count": audio_results.get("word_count", 0),
            "filler_count": audio_results.get("filler_count", 0)
        },
        
        # 📝 D. TRANSCRIPT ANALYSIS
        "transcript_analysis": {
            "transcript_confidence_level": transcript_results.get("transcript_confidence_level", 0),
            "speech_content_density": transcript_results.get("speech_content_density", 0),
            "filler_word_frequency": transcript_results.get("filler_word_frequency", 0),
            "sentiment_polarity_trend": transcript_results.get("sentiment_polarity_trend", {}),
            "emotional_language_usage": transcript_results.get("emotional_language_usage", {}),
            "cognitive_distortion_indicators": transcript_results.get("cognitive_distortion_indicators", []),
            "crisis_keyword_presence": transcript_results.get("crisis_keyword_presence", {})
        },
        
        # 🧠 E. SUMMARY
        "summary": {
            "observational_summary": transcript_results.get("observational_summary", ""),
            "detected_strengths": transcript_results.get("detected_strengths", [])
        },
        
        # Legacy fields for backward compatibility
        "confidence_score": calculate_overall_confidence(audio_results, transcript_results, aggregated_video),
        "generated_at": time.time()
    }
    
    return report


def aggregate_video_metrics(video_results):
    """
    Aggregate video metrics from multiple participants
    """
    if not video_results:
        return {}
    
    # For now, just use the first participant's metrics
    # In a real scenario, you might average or combine metrics
    first_participant = list(video_results.values())[0]
    
    return {
        "dominant_emotion_distribution": first_participant.get("dominant_emotion_distribution", {}),
        "facial_emotional_variability": first_participant.get("facial_emotional_variability", 0),
        "facial_tension_index": first_participant.get("facial_tension_index", 0),
        "eye_contact_consistency": first_participant.get("eye_contact_consistency", 0),
        "head_movement_patterns": first_participant.get("head_movement_patterns", {}),
        "facial_expressiveness_score": first_participant.get("facial_expressiveness_score", 0),
        "stress_expression_frequency": first_participant.get("stress_expression_frequency", 0)
    }


def calculate_overall_confidence(audio_results, transcript_results, video_metrics):
    """
    Calculate overall confidence score for the analysis
    """
    
    # Weight different components
    transcript_conf = transcript_results.get("transcript_confidence_level", 0)
    fluency_score = audio_results.get("speech_fluency_score", 0)
    
    # Average confidence
    overall = (transcript_conf * 0.5) + (fluency_score * 0.5)
    
    return round(overall, 2)

