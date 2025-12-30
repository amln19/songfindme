#!/bin/bash

echo "🎵 SongFindMe Setup Script"
echo "=========================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "❌ Python 3 not found. Please install Python 3.9+"; exit 1; }

# Check if PostgreSQL is installed
echo "Checking PostgreSQL..."
command -v psql >/dev/null 2>&1 || { echo "⚠️  PostgreSQL not found. Please install PostgreSQL."; }

# Check if FFmpeg is installed
echo "Checking FFmpeg..."
command -v ffmpeg >/dev/null 2>&1 || { echo "⚠️  FFmpeg not found. Please install FFmpeg."; }

# Check Node.js
echo "Checking Node.js..."
node --version || { echo "❌ Node.js not found. Please install Node.js 18+"; exit 1; }

echo ""
echo "Setting up backend..."
echo "---------------------"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r backend/requirements.txt

# Create .env files if they don't exist
if [ ! -f "backend/.env" ]; then
    echo "Creating backend/.env from template..."
    cp .env.example backend/.env
    echo "⚠️  Please edit backend/.env with your configuration!"
fi

echo ""
echo "Setting up frontend..."
echo "---------------------"
cd frontend

# Install Node dependencies
echo "Installing Node dependencies..."
npm install

# Create frontend .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating frontend/.env from template..."
    cp ../.env.example .env
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your database credentials and generate a SECRET_KEY"
echo "2. Ensure PostgreSQL is running"
echo "3. Run 'npm run dev:backend' in one terminal"
echo "4. Run 'npm run dev:frontend' in another terminal"
echo ""
echo "Happy coding! 🎉"