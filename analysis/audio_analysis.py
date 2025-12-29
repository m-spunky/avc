
import whisper
import os
import numpy as np

model = None

def load_model():
    global model
    if model is None:
        print("Loading Whisper model...")
        # Use 'base' or 'tiny' for speed on CPU
        model = whisper.load_model("base")

def analyze_audio(audio_path: str):
    """
    Transcribes audio and extracts comprehensive speech metrics.
    """
    if not os.path.exists(audio_path):
         return {"error": "Audio file not found"}

    load_model()
    
    print(f"Transcribing {audio_path}...")
    result = model.transcribe(audio_path, word_timestamps=True)
    
    segments = result["segments"]
    full_text = result["text"]
    
    # Calculate basic metrics
    filler_words = ["um", "uh", "ah", "like", "you know", "sort of", "kind of"]
    filler_count = 0
    words = full_text.lower().split()
    for w in words:
        if w in filler_words:
            filler_count += 1
    
    # Calculate pauses (gaps between segments)
    pause_data = calculate_pause_metrics(segments)
    
    # Calculate speech rate (words per minute)
    speech_rate = calculate_speech_rate(segments, len(words))
    
    # Calculate pitch and volume metrics using librosa (if available)
    try:
        import librosa
        acoustic_features = extract_acoustic_features(audio_path)
    except ImportError:
        print("Warning: librosa not installed. Using basic acoustic analysis.")
        acoustic_features = get_basic_acoustic_features()
    
    # Calculate speech fluency score
    fluency_score = calculate_fluency_score(
        filler_count, 
        len(words), 
        pause_data["long_pauses"],
        pause_data["pause_frequency"]
    )
    
    return {
        # Basic transcription
        "transcript": full_text,
        "word_count": len(words),
        "segments": segments,
        
        # Speech metrics
        "filler_count": filler_count,
        "filler_word_frequency": round((filler_count / len(words) * 100), 2) if len(words) > 0 else 0,
        
        # Pause metrics
        "pause_frequency": pause_data["pause_frequency"],
        "average_pause_duration": pause_data["average_pause_duration"],
        "long_pauses": pause_data["long_pauses"],
        
        # Speech rate
        "speech_rate_wpm": speech_rate,
        
        # Acoustic features
        "pitch_variability": acoustic_features["pitch_variability"],
        "volume_stability": acoustic_features["volume_stability"],
        "voice_stress_indicator": acoustic_features["voice_stress_indicator"],
        "vocal_tremor_detected": acoustic_features["vocal_tremor_detected"],
        
        # Composite scores
        "speech_fluency_score": fluency_score
    }


def calculate_pause_metrics(segments):
    """
    Calculate pause frequency and average duration
    """
    pauses = []
    long_pauses = 0
    
    for i in range(1, len(segments)):
        gap = segments[i]["start"] - segments[i-1]["end"]
        if gap > 0.5:  # Pauses longer than 0.5 seconds
            pauses.append(gap)
            if gap > 2.0:  # Long pauses > 2 seconds
                long_pauses += 1
    
    pause_frequency = len(pauses)
    average_pause_duration = round(np.mean(pauses), 2) if pauses else 0.0
    
    return {
        "pause_frequency": pause_frequency,
        "average_pause_duration": average_pause_duration,
        "long_pauses": long_pauses
    }


def calculate_speech_rate(segments, word_count):
    """
    Calculate words per minute
    """
    if not segments or word_count == 0:
        return 0.0
    
    # Total speaking time (excluding pauses)
    speaking_time = 0
    for seg in segments:
        speaking_time += (seg["end"] - seg["start"])
    
    if speaking_time == 0:
        return 0.0
    
    # Words per minute
    wpm = (word_count / speaking_time) * 60
    return round(wpm, 2)


def extract_acoustic_features(audio_path):
    """
    Extract acoustic features using librosa
    """
    import librosa
    
    # Load audio
    y, sr = librosa.load(audio_path, sr=16000)
    
    # Extract pitch (F0) using piptrack
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    
    # Get pitch values (non-zero)
    pitch_values = []
    for t in range(pitches.shape[1]):
        index = magnitudes[:, t].argmax()
        pitch = pitches[index, t]
        if pitch > 0:
            pitch_values.append(pitch)
    
    # Calculate pitch variability (standard deviation)
    pitch_variability = round(np.std(pitch_values), 2) if pitch_values else 0.0
    
    # Extract RMS energy for volume analysis
    rms = librosa.feature.rms(y=y)[0]
    volume_stability = round(100 - (np.std(rms) / np.mean(rms) * 100), 2) if len(rms) > 0 else 0.0
    volume_stability = max(0, min(100, volume_stability))  # Clamp to 0-100
    
    # Voice stress indicator (composite of pitch and energy variance)
    # Higher variance = higher stress
    stress_score = calculate_stress_score(pitch_values, rms)
    
    # Vocal tremor detection (high-frequency pitch variations)
    tremor_detected = detect_vocal_tremor(pitch_values)
    
    return {
        "pitch_variability": pitch_variability,
        "volume_stability": volume_stability,
        "voice_stress_indicator": stress_score,
        "vocal_tremor_detected": tremor_detected
    }


def get_basic_acoustic_features():
    """
    Fallback when librosa is not available
    """
    return {
        "pitch_variability": 0.0,
        "volume_stability": 75.0,  # Neutral default
        "voice_stress_indicator": 50.0,  # Neutral default
        "vocal_tremor_detected": False
    }


def calculate_stress_score(pitch_values, rms_values):
    """
    Calculate voice stress indicator from acoustic features
    Score: 0-100 (higher = more stress)
    """
    if not pitch_values or len(rms_values) == 0:
        return 50.0  # Neutral
    
    # Normalize pitch variance (0-100 scale)
    pitch_std = np.std(pitch_values)
    pitch_score = min(100, (pitch_std / 50) * 100)  # Normalize assuming max std ~50Hz
    
    # Normalize energy variance
    rms_std = np.std(rms_values)
    rms_mean = np.mean(rms_values)
    energy_score = min(100, (rms_std / rms_mean) * 100) if rms_mean > 0 else 0
    
    # Composite stress score (weighted average)
    stress_score = (pitch_score * 0.6) + (energy_score * 0.4)
    
    return round(stress_score, 2)


def detect_vocal_tremor(pitch_values):
    """
    Detect vocal tremor from pitch variations
    Tremor is characterized by rapid, regular pitch oscillations
    """
    if not pitch_values or len(pitch_values) < 10:
        return False
    
    # Calculate consecutive pitch differences
    pitch_diffs = np.diff(pitch_values)
    
    # High frequency of direction changes indicates tremor
    direction_changes = 0
    for i in range(1, len(pitch_diffs)):
        if (pitch_diffs[i] > 0) != (pitch_diffs[i-1] > 0):
            direction_changes += 1
    
    # If more than 60% of samples show direction changes, likely tremor
    tremor_ratio = direction_changes / len(pitch_diffs)
    
    return tremor_ratio > 0.6


def calculate_fluency_score(filler_count, word_count, long_pauses, pause_frequency):
    """
    Calculate speech fluency score (0-100, higher is better)
    """
    if word_count == 0:
        return 0.0
    
    # Penalize fillers
    filler_penalty = (filler_count / word_count) * 100
    
    # Penalize long pauses
    pause_penalty = long_pauses * 5
    
    # Penalize excessive pauses
    pause_rate_penalty = min(30, pause_frequency * 2)
    
    # Start with 100 and subtract penalties
    fluency = 100 - filler_penalty - pause_penalty - pause_rate_penalty
    fluency = max(0, min(100, fluency))  # Clamp to 0-100
    
    return round(fluency, 2)

