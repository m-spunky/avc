# Scenario-Based AVC - Quick Start Guide

## 🚀 Quick Test

### 1. Start the Server
```bash
python app.py
```

### 2. Add a Test Scenario Video

**Option A: Use existing video**
- Copy any MP4 video to: `storage/scenarios/demo_scenario/video.mp4`
- The demo scenario metadata is already created

**Option B: Use one of your existing session videos**
```bash
# Copy an existing session video as a scenario
copy storage\28eb59ba\merged\full_session.mp4 storage\scenarios\demo_scenario\video.mp4
```

### 3. Test the Flow

1. **Browse Scenarios**
   - Navigate to: `http://localhost:8000/scenario`
   - You should see the "Anxiety Management Practice" scenario

2. **Start Practice**
   - Click "Start Practice →"
   - Allow camera/microphone access
   - Click "Start Practice Session"

3. **Record Your Response**
   - The scenario video will play
   - Your camera will record your response
   - Speak naturally as if responding to the scenario

4. **End Session**
   - Click "End Session & View Report"
   - Wait for analysis (1-2 minutes)

5. **View Report**
   - See step-wise behavioral analysis
   - Review overall performance metrics
   - Check insights and strengths

---

## 📁 Project Structure

```
avc/
├── app.py                          # FastAPI server with scenario endpoints
├── storage/
│   ├── scenarios/                  # Scenario videos
│   │   └── demo_scenario/
│   │       ├── metadata.json       # ✅ Created
│   │       └── video.mp4           # ⚠️ Add your video here
│   └── scenario_sessions/          # User practice sessions
│       └── {session_id}/
│           ├── raw/user.webm
│           ├── merged/user_session.mp4
│           ├── audio/user_audio.wav
│           └── report/report.json
├── static/
│   ├── scenario.html               # ✅ Scenario selection page
│   ├── practice.html               # ✅ Practice session page
│   ├── scenario_report.html        # ✅ Step-wise report page
│   └── js/
│       ├── scenario.js             # ✅ Selection logic
│       ├── practice.js             # ✅ Recording & session management
│       └── scenario_report.js      # ✅ Report visualization
└── analysis/
    └── pipeline.py                 # ✅ Integrated with step-wise analysis
```

---

## 🎯 API Endpoints

### Scenario Management
- `GET /api/scenarios` - List all scenarios
- `GET /api/scenarios/{id}` - Get scenario details
- `POST /api/scenarios` - Upload new scenario (admin)

### Session Management
- `POST /api/scenario/start` - Start practice session
- `POST /api/scenario/upload/{session_id}` - Upload recording chunks
- `POST /api/scenario/end/{session_id}` - End session & analyze
- `GET /api/scenario/report/{session_id}` - Get step-wise report

### Pages
- `/scenario` - Browse scenarios
- `/practice/{session_id}` - Practice session
- `/scenario_report/{session_id}` - View report

---

## 🎬 Creating More Scenarios

### Manual Method

1. Create scenario folder:
```bash
mkdir storage\scenarios\my_scenario
```

2. Add video file:
```
storage/scenarios/my_scenario/video.mp4
```

3. Create metadata.json:
```json
{
  "id": "my_scenario",
  "title": "Your Scenario Title",
  "description": "Scenario description",
  "video_path": "/storage/scenarios/my_scenario/video.mp4",
  "duration": 120.0,
  "steps": [
    {"time": 0, "title": "Step 1", "description": "Description"},
    {"time": 30, "title": "Step 2", "description": "Description"}
  ],
  "created_at": 1735365000
}
```

### API Method

```bash
curl -X POST http://localhost:8000/api/scenarios \
  -F "title=My Scenario" \
  -F "description=Practice scenario" \
  -F 'steps=[{"time":0,"title":"Intro","description":"Start"}]' \
  -F "video=@path/to/video.mp4"
```

---

## ✅ What's Implemented

- ✅ Complete backend API (6 endpoints)
- ✅ Scenario selection UI
- ✅ Practice session with WebRTC recording
- ✅ Step-wise analysis integration
- ✅ Comprehensive report visualization
- ✅ Chunk-based upload (no data loss)
- ✅ All 32+ behavioral metrics
- ✅ Reuses existing analysis pipeline

---

## 🔧 Troubleshooting

**Scenario not showing?**
- Check `storage/scenarios/demo_scenario/metadata.json` exists
- Ensure `video.mp4` is in the same folder
- Refresh the page

**Camera not working?**
- Allow browser permissions
- Use HTTPS or localhost
- Check browser console for errors

**Analysis stuck?**
- Check terminal for error messages
- Verify FFmpeg is installed
- Check `storage/scenario_sessions/{session_id}/` for files

**Report not loading?**
- Wait 1-2 minutes for analysis
- Check browser console
- Verify report.json exists in session folder

---

## 🎓 Next Steps

1. **Test with real scenario video**
2. **Practice multiple sessions**
3. **Compare reports over time**
4. **Add more scenarios** for different therapy situations

Enjoy practicing! 🎉
