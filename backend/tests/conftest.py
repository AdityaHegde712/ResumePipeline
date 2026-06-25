"""
Pytest fixtures for data layer tests.
"""
import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def tmp_data_dir():
    """Create a temporary directory for test data files."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_sweep_file(tmp_data_dir):
    """Create a minimal sweep markdown file with 3 fake projects."""
    content = """# Project Sweep Summaries

## 1. ARVR — Full-Stack Web Application
**Type:** Full-Stack Web Application
**Tech Stack:** React, TypeScript, Node.js, PostgreSQL, Docker, WebSocket

### Project Overview
A collaborative AR/VR project management platform.

### Key Features
- **Real-time Collaboration:** WebSocket-based multi-user editing
- **3D Visualization:** Three.js-based project timeline

### Resume Value
- Built a real-time collaborative platform serving 100+ users
- Architected WebSocket infrastructure reducing latency by 60%

---

## 2. Sentry — Computer Vision
**Type:** ML Research Project
**Tech Stack:** Python, PyTorch, OpenCV, YOLO, CUDA

### Project Overview
Real-time video monitoring system using computer vision.

### Key Features
- **Object Detection:** YOLO-based real-time detection at 30fps
- **Alert System:** Automated notification pipeline

### Resume Value
- Achieved 95% detection accuracy on custom dataset
- Optimized inference pipeline for 30fps real-time processing

---

## 3. DailyBrief — Python CLI Tool
**Type:** Python CLI Tool
**Tech Stack:** Python, Click, SQLite, Redis, Docker

### Project Overview
Daily briefing automation tool with email integration.

### Key Features
- **News Aggregation:** RSS feed parsing with ML-based filtering
- **Email Digest:** Automated morning briefing delivery

### Resume Value
- Reduced daily briefing time by 80% for team of 50
- Built scalable pipeline processing 500+ articles daily
"""
    f = tmp_data_dir / "PROJECT_SWEEP_SUMMARIES.md"
    f.write_text(content, encoding="utf-8")
    return f
