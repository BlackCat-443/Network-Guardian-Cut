#!/bin/bash
# start_netcut.sh
# Jalankan dengan: sudo ./start_netcut.sh

echo "========================================"
echo "🔥 NETCUT ARP SPOOFING - SHADOW EDITION"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ ERROR: This script must run as root!"
    echo "   Usage: sudo ./start_netcut.sh"
    echo ""
    exit 1
fi

cd /home/banh-code/Documents/tools/Network-Guardian-rename

echo "📂 Working directory: $(pwd)"
echo ""

echo "🔧 Setting up network..."
# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward
echo "   ✅ IP forwarding enabled"

# Setup iptables
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT
echo "   ✅ iptables reset"

echo ""
echo "🐍 Checking Python environment..."
# Check if venv exists
if [ -d "venv" ]; then
    echo "   ✅ Virtual environment found"
    
    # Check Python in venv
    if [ -f "venv/bin/python" ]; then
        echo "   ✅ Python found in venv: $(venv/bin/python --version 2>&1)"
        
        # Check Flask installation in venv
        if venv/bin/python -c "import flask" 2>/dev/null; then
            echo "   ✅ Flask is installed in venv"
        else
            echo "   ❌ Flask NOT found in venv!"
            echo "   Installing requirements in venv..."
            venv/bin/pip install -r requirements.txt
        fi
    else
        echo "   ❌ Python not found in venv!"
        exit 1
    fi
else
    echo "   ❌ Virtual environment not found!"
    echo "   Creating venv..."
    python3 -m venv venv
    venv/bin/pip install -r requirements.txt
fi

echo ""
echo "🚀 Starting NetCut Engine..."
echo "========================================"
echo ""

# Gunakan Python dari venv dengan sudo (karena sudah sebagai root)
./venv/bin/python app.py