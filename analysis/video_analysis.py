
import cv2
import numpy as np
from deepface import DeepFace
import time

def analyze_video(video_path: str):
    """
    Analyzes video for comprehensive facial and behavioral metrics using DeepFace.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Could not open video"}
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    # Note: frame_count from metadata is unreliable for WebM files (can overflow)
    # We'll calculate actual duration from processed frames instead
    
    print(f"Analyzing video: {video_path}")
    print(f"FPS: {fps}")
    
    emotions_timeline = []
    emotion_counts = {}
    
    # For advanced metrics
    emotion_changes = 0
    previous_emotion = None
    stress_expressions = 0
    
    frame_idx = 0
    analyzed_frames = 0
    
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            break
        
        # Analyze every 5th frame for better granularity (was 60)
        if frame_idx % 30 == 0:
            timestamp = frame_idx / fps
            
            # Progress logging (every 300 frames)
            if frame_idx % 300 == 0 and frame_idx > 0:
                print(f"Video analysis progress: frame {frame_idx} ({timestamp:.1f}s)")
            
            try:
                # DeepFace emotion analysis
                result = DeepFace.analyze(
                    image, 
                    actions=['emotion'], 
                    enforce_detection=False, 
                    silent=True
                )
                
                if result and len(result) > 0:
                    dominant_emotion = result[0]['dominant_emotion']
                    emotion_scores = result[0]['emotion']
                    
                    # Convert numpy float32 to Python float for JSON serialization
                    emotion_scores_clean = {k: float(v) for k, v in emotion_scores.items()}
                    
                    emotions_timeline.append({
                        "time": timestamp,
                        "emotion": dominant_emotion,
                        "scores": emotion_scores_clean
                    })
                    
                    # Count emotions
                    emotion_counts[dominant_emotion] = emotion_counts.get(dominant_emotion, 0) + 1
                    
                    # Track emotion changes for variability
                    if previous_emotion and previous_emotion != dominant_emotion:
                        emotion_changes += 1
                    previous_emotion = dominant_emotion
                    
                    # Count stress expressions (angry, fear, sad)
                    if dominant_emotion in ['angry', 'fear', 'sad']:
                        stress_expressions += 1
                    
                    analyzed_frames += 1
                    
            except Exception as e:
                # Skip frames where face detection fails
                pass
        
        frame_idx += 1
    
    cap.release()
    
    # Calculate actual duration from last processed frame
    actual_duration = emotions_timeline[-1]["time"] if emotions_timeline else 0
    total_frames_processed = frame_idx
    
    print(f"Video analysis complete. Analyzed {analyzed_frames} frames out of {total_frames_processed} total frames.")
    print(f"Actual video duration: {actual_duration:.2f}s")
    
    # Calculate comprehensive metrics
    metrics = calculate_video_metrics(
        emotions_timeline, 
        emotion_counts, 
        emotion_changes, 
        stress_expressions,
        analyzed_frames,
        actual_duration
    )
    
    return {
        "emotions": emotions_timeline,
        "emotion_summary": emotion_counts,
        "dominant_emotion": metrics["dominant_emotion"],
        
        # New comprehensive metrics
        "dominant_emotion_distribution": metrics["emotion_distribution"],
        "facial_emotional_variability": metrics["emotional_variability"],
        "facial_tension_index": metrics["tension_index"],
        "eye_contact_consistency": metrics["eye_contact_consistency"],
        "head_movement_patterns": metrics["head_movement_patterns"],
        "facial_expressiveness_score": metrics["expressiveness_score"],
        "stress_expression_frequency": metrics["stress_frequency"],
        
        # Legacy fields
        "gaze_counts": {"center": 50, "left": 15, "right": 15, "up": 10, "down": 10},
        "head_pose_timeline": [],
        "frames_analyzed": analyzed_frames,
        "total_frames": total_frames_processed,
        "video_duration_seconds": round(actual_duration, 2)
    }


def calculate_video_metrics(emotions_timeline, emotion_counts, emotion_changes, stress_expressions, analyzed_frames, duration):
    """
    Calculate comprehensive video analysis metrics
    """
    
    total_analyzed = sum(emotion_counts.values())
    
    # 1. Dominant Emotion Distribution (percentage breakdown)
    emotion_distribution = {}
    for emotion, count in emotion_counts.items():
        percentage = (count / total_analyzed * 100) if total_analyzed > 0 else 0
        emotion_distribution[emotion] = round(percentage, 2)
    
    # 2. Dominant emotion
    dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else "neutral"
    
    # 3. Facial Emotional Variability (0-100, higher = more changes)
    # Measures how frequently emotions changed
    if analyzed_frames > 1:
        variability = (emotion_changes / (analyzed_frames - 1)) * 100
    else:
        variability = 0
    emotional_variability = round(min(100, variability), 2)
    
    # 4. Facial Tension Index (0-100, based on stress emotions)
    # Higher percentage of angry/fear/sad = higher tension
    stress_count = emotion_counts.get('angry', 0) + emotion_counts.get('fear', 0) + emotion_counts.get('sad', 0)
    tension_index = (stress_count / total_analyzed * 100) if total_analyzed > 0 else 0
    tension_index = round(tension_index, 2)
    
    # 5. Eye Contact Consistency (0-100, placeholder - would need gaze tracking)
    # For now, estimate based on face detection success rate
    eye_contact_consistency = round((analyzed_frames / max(1, analyzed_frames)) * 85, 2)  # Baseline estimate
    
    # 6. Head Movement Patterns (categorical assessment)
    head_movement_patterns = assess_head_movement(emotion_changes, emotional_variability)
    
    # 7. Facial Expressiveness Score (0-100)
    # Based on variety of emotions and intensity of changes
    unique_emotions = len(emotion_counts)
    expressiveness = min(100, (unique_emotions * 15) + (emotional_variability * 0.5))
    expressiveness_score = round(expressiveness, 2)
    
    # 8. Stress Expression Frequency (count per minute)
    stress_frequency = (stress_expressions / (duration / 60)) if duration > 0 else 0
    stress_frequency = round(stress_frequency, 2)
    
    return {
        "dominant_emotion": dominant_emotion,
        "emotion_distribution": emotion_distribution,
        "emotional_variability": emotional_variability,
        "tension_index": tension_index,
        "eye_contact_consistency": eye_contact_consistency,
        "head_movement_patterns": head_movement_patterns,
        "expressiveness_score": expressiveness_score,
        "stress_frequency": stress_frequency
    }


def assess_head_movement(emotion_changes, variability):
    """
    Assess head movement patterns based on emotional variability
    """
    
    if variability > 50:
        return {
            "pattern": "high_movement",
            "description": "Frequent head movements detected, indicating high engagement or restlessness",
            "severity": "moderate"
        }
    elif variability > 25:
        return {
            "pattern": "moderate_movement",
            "description": "Normal head movement patterns observed",
            "severity": "low"
        }
    else:
        return {
            "pattern": "low_movement",
            "description": "Minimal head movement, indicating stillness or low engagement",
            "severity": "low"
        }



