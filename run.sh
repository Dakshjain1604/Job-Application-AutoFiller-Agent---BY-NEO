#!/bin/bash
# AutoCareer Application Startup Script

echo "=========================================="
echo "  AutoCareer - Job Application Automation"
echo "=========================================="
echo ""

PROJECT_DIR="/root/jobApplicationAutoFiller"

# Check if backend port is available
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 already in use. Stopping existing backend..."
    kill $(lsof -t -i:8000) 2>/dev/null
    sleep 2
fi

# Check if frontend port is available
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 3000 already in use. Stopping existing frontend..."
    kill $(lsof -t -i:3000) 2>/dev/null
    sleep 2
fi

echo "Starting Backend (FastAPI on port 8000)..."
cd "$PROJECT_DIR/backend"
source "$PROJECT_DIR/venv/bin/activate"
nohup python main.py > "$PROJECT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "✓ Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "Waiting for backend to initialize..."
for i in {1..10}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "✓ Backend is ready"
        break
    fi
    sleep 1
done

echo ""
echo "Starting Frontend (React on port 3000)..."
cd "$PROJECT_DIR/frontend"
nohup npm start > "$PROJECT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "✓ Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "=========================================="
echo "  🚀 AutoCareer is starting up!"
echo "=========================================="
echo ""
echo "Backend API:  http://localhost:8000"
echo "Frontend App: http://localhost:3000"
echo "API Docs:     http://localhost:8000/docs"
echo ""
echo "Backend logs: tail -f $PROJECT_DIR/backend.log"
echo "Frontend logs: tail -f $PROJECT_DIR/frontend.log"
echo ""
echo "To stop the application:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "⏳ Frontend may take 10-20 seconds to build..."
echo "   Then open: http://localhost:3000"
echo ""
echo "=========================================="

# Keep script running to show logs
echo "Press Ctrl+C to view logs (services will keep running in background)"
sleep 3
echo ""
echo "Recent backend logs:"
tail -20 "$PROJECT_DIR/backend.log"
