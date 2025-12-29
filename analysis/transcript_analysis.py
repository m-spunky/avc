"""
Transcript Analysis Module using OpenRouter LLM
Analyzes speech transcripts for psychological and behavioral insights
"""

import os
import json
import requests
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def analyze_transcript(transcript: str, segments: List[Dict], word_count: int, filler_count: int) -> Dict[str, Any]:
    """
    Analyzes transcript using OpenRouter LLM for psychological insights
    
    Args:
        transcript: Full transcript text
        segments: Whisper segments with timestamps
        word_count: Total word count
        filler_count: Count of filler words
        
    Returns:
        Dictionary with transcript analysis metrics
    """
    
    # Calculate basic metrics
    total_duration = segments[-1]["end"] if segments else 0
    speech_content_density = calculate_content_density(segments, total_duration)
    
    # Calculate transcript confidence from Whisper segments
    transcript_confidence = calculate_transcript_confidence(segments)
    
    # Use LLM for advanced analysis
    llm_analysis = analyze_with_llm(transcript)
    
    return {
        # Basic metrics
        "transcript_confidence_level": transcript_confidence,
        "speech_content_density": speech_content_density,
        "filler_word_frequency": filler_count,
        
        # LLM-powered analysis
        "sentiment_polarity_trend": llm_analysis.get("sentiment_trend", {}),
        "emotional_language_usage": llm_analysis.get("emotional_language", {}),
        "cognitive_distortion_indicators": llm_analysis.get("cognitive_distortions", []),
        "crisis_keyword_presence": llm_analysis.get("crisis_indicators", {}),
        
        # Summary
        "observational_summary": llm_analysis.get("observational_summary", ""),
        "detected_strengths": llm_analysis.get("strength_indicators", [])
    }


def calculate_content_density(segments: List[Dict], total_duration: float) -> float:
    """
    Calculate ratio of speech time to total duration
    """
    if total_duration == 0:
        return 0.0
    
    speech_time = 0
    for seg in segments:
        speech_time += (seg["end"] - seg["start"])
    
    density = (speech_time / total_duration) * 100
    return round(density, 2)


def calculate_transcript_confidence(segments: List[Dict]) -> float:
    """
    Calculate average confidence from Whisper segments
    Higher no_speech_prob = lower confidence
    """
    if not segments:
        return 0.0
    
    confidence_scores = []
    for seg in segments:
        # Whisper provides no_speech_prob - invert it for confidence
        no_speech_prob = seg.get("no_speech_prob", 0.5)
        confidence = (1 - no_speech_prob) * 100
        confidence_scores.append(confidence)
    
    avg_confidence = sum(confidence_scores) / len(confidence_scores)
    return round(avg_confidence, 2)


def analyze_with_llm(transcript: str) -> Dict[str, Any]:
    """
    Send transcript to OpenRouter LLM for psychological analysis
    """
    
    if not OPENROUTER_API_KEY:
        print("Warning: OPENROUTER_API_KEY not set. Using fallback analysis.")
        return get_fallback_analysis(transcript)
    
    # Construct prompt for structured psychological analysis
    prompt = f"""You are a clinical psychologist analyzing a therapy session transcript. Provide a structured, observational analysis without making diagnoses.

Transcript:
{transcript}

Please analyze the transcript and provide a JSON response with the following structure:

{{
  "sentiment_trend": {{
    "overall": "positive/neutral/negative",
    "trajectory": "improving/stable/declining",
    "confidence": 0-100
  }},
  "emotional_language": {{
    "fear_words": ["list", "of", "words"],
    "stress_words": ["list", "of", "words"],
    "confidence_words": ["list", "of", "words"],
    "calm_words": ["list", "of", "words"],
    "total_emotional_words": 0
  }},
  "cognitive_distortions": [
    {{
      "type": "catastrophizing/black-and-white/overgeneralization/etc",
      "example": "quote from transcript",
      "severity": "mild/moderate/significant"
    }}
  ],
  "crisis_indicators": {{
    "self_harm_references": false,
    "hopelessness_language": false,
    "crisis_keywords_found": [],
    "risk_level": "none/low/moderate/high"
  }},
  "observational_summary": "2-3 sentence neutral description of behavioral patterns observed",
  "strength_indicators": [
    "Observable strength 1",
    "Observable strength 2"
  ]
}}

Respond ONLY with valid JSON. Be objective and observational, not diagnostic."""

    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "AVC Therapy Analysis"
        }
        
        payload = {
            "model": "anthropic/claude-3.5-sonnet",  # High-quality model for psychological analysis
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Lower temperature for more consistent analysis
            "max_tokens": 2000
        }
        
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Parse JSON response
        analysis = json.loads(content)
        return analysis
        
    except Exception as e:
        print(f"LLM analysis failed: {e}")
        return get_fallback_analysis(transcript)


def get_fallback_analysis(transcript: str) -> Dict[str, Any]:
    """
    Fallback analysis using basic keyword matching when LLM is unavailable
    """
    
    words = transcript.lower().split()
    
    # Basic keyword dictionaries
    fear_keywords = ["afraid", "scared", "anxious", "worry", "fear", "nervous", "terrified"]
    stress_keywords = ["stress", "overwhelmed", "pressure", "tense", "exhausted", "burnout"]
    confidence_keywords = ["confident", "capable", "strong", "able", "succeed", "achieve"]
    calm_keywords = ["calm", "peaceful", "relaxed", "comfortable", "ease", "serene"]
    crisis_keywords = ["suicide", "kill myself", "end it", "hopeless", "worthless", "give up"]
    
    # Count emotional words
    fear_words = [w for w in words if w in fear_keywords]
    stress_words = [w for w in words if w in stress_keywords]
    confidence_words = [w for w in words if w in confidence_keywords]
    calm_words = [w for w in words if w in calm_keywords]
    crisis_words = [w for w in words if w in crisis_keywords]
    
    # Determine sentiment
    positive_count = len(confidence_words) + len(calm_words)
    negative_count = len(fear_words) + len(stress_words)
    
    if positive_count > negative_count:
        overall_sentiment = "positive"
    elif negative_count > positive_count:
        overall_sentiment = "negative"
    else:
        overall_sentiment = "neutral"
    
    return {
        "sentiment_trend": {
            "overall": overall_sentiment,
            "trajectory": "stable",
            "confidence": 60
        },
        "emotional_language": {
            "fear_words": fear_words[:5],
            "stress_words": stress_words[:5],
            "confidence_words": confidence_words[:5],
            "calm_words": calm_words[:5],
            "total_emotional_words": len(fear_words) + len(stress_words) + len(confidence_words) + len(calm_words)
        },
        "cognitive_distortions": [],
        "crisis_indicators": {
            "self_harm_references": len(crisis_words) > 0,
            "hopelessness_language": "hopeless" in words or "worthless" in words,
            "crisis_keywords_found": crisis_words,
            "risk_level": "high" if len(crisis_words) > 0 else "none"
        },
        "observational_summary": f"Session transcript contains {len(words)} words with {overall_sentiment} sentiment overall.",
        "strength_indicators": ["Engaged in session", "Completed full session"] if len(words) > 50 else []
    }
