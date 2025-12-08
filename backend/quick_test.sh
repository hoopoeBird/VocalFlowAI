#!/bin/bash
echo "=== Phase 2 Quick Test ==="
echo ""
echo "1. Checking server status..."
curl -s http://localhost:8000/health && echo "" || echo "❌ Server not running! Start with: uvicorn app.main:app --reload"
echo ""
echo "2. Starting test client..."
echo "   (Speak into your microphone, press Ctrl+C to stop)"
echo ""
python test_client.py
