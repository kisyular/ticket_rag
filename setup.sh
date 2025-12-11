#!/bin/bash
# Quick setup script for Ticket RAG System

echo "Setting up Ticket RAG System..."
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
if (( $(echo "$python_version < 3.8" | bc -l) )); then
    echo "Python 3.8+ required. Current version: $python_version"
    exit 1
fi
echo "Python $python_version"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "Dependencies installed"
echo ""

# Download embedding model (happens automatically on first run)
echo "Downloading embedding model (first run only)..."
python3 << EOF
from sentence_transformers import SentenceTransformer
print("Loading model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model downloaded and ready")
EOF
echo ""

# Create directory structure
echo "Creating directory structure..."
mkdir -p chroma_db
mkdir -p templates/tickets
echo "Directories created"
echo ""

# Test installation
echo "Testing installation..."
python3 << EOF
try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    print("All imports successful")
except Exception as e:
    print(f"Import error: {e}")
    exit(1)
EOF
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo ""
echo "1. Run the demo:"
echo "   python demo.py"
echo ""
echo "2. For Django integration:"
echo "   - Copy files to your Django app"
echo "   - Run: python manage.py sync_tickets_to_rag"
echo ""
echo "3. (Optional) Install Ollama for LLM generation:"
echo "   - Download: https://ollama.ai/download"
echo "   - Run: ollama run llama2"
echo ""
echo "Read README.md for full documentation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
