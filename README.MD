# 🌐 Network Guardian

![Network Guardian](https://raw.githubusercontent.com/BlackCat-443/Network-Guardian/main/images/images.png)

## 📱 A powerful network monitoring and control application

Network Guardian is a web-based dashboard that gives you complete visibility and control over your local network. Monitor connected devices, track network traffic, and manage unwanted connections - all from a simple and intuitive interface.

## ✨ Features

- **Real-time Device Discovery**: Automatically scan and detect all devices connected to your network
- **Traffic Monitoring**: Track upload and download rates with historical data visualization
- **System Information**: View detailed information about your system and network configuration
- **Access Control**:
  - 🚫 Block Devices: Prevent specific devices from accessing your network *(Still in development)*
  - 🛢️ Kick Devices: Temporarily disconnect devices from your network *(Still in development)*
- **Customizable Scanning**: Adjust scan intervals based on your needs
- **Responsive Dashboard**: Access from any device with a web browser

## ⚠️ Important Notice

> The **"Block"** and **"Kick"** features are under development. They may not behave as expected or may require additional configuration (e.g., running with administrator/root privileges). Use these features with caution.

## 🚀 Quick Start

### Prerequisites

- Python 3.6+
- pip (Python package manager) New Version

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/BlackCat-443/Network-Guardian.git
   cd network-guardian
   ```
2. (Optional) If you encounter issues, use a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
4. Run the application:
   ```
   sudo ./start_netcut.sh
   ```
5. Open your browser and navigate to:
   ```
   http://localhost:8686
   ```

> ⚠️ **Note:** Some features like blocking and kicking devices require administrative privileges. On Linux/Mac, run with `sudo ./start_netcut.sh` for full functionality.

## 🛠️ Dashboard Pages

### 💻 Devices Page

![Network Devices](https://github.com/BlackCat-443/Network-Guardian/blob/main/images/devices.png?raw=true)

- Displays all detected devices on the network
- Shows IP addresses, MAC addresses, and connection status
- Provides options to **Block** or **Kick** devices *(in development)*

### 🌐 Network Settings Page

![Settings Page](https://raw.githubusercontent.com/BlackCat-443/Network-Guardian/main/images/settings.png)

- Customize scan intervals
- Adjust network monitoring preferences
- Toggle security settings

### 📊 Real-time Traffic Chart

![Live Traffic](https://raw.githubusercontent.com/BlackCat-443/Network-Guardian/main/images/live_traffic.png)

- Displays real-time upload and download activity
- Helps in identifying bandwidth usage spikes

### 📊 System Information Page

![System Info](https://raw.githubusercontent.com/BlackCat-443/Network-Guardian/main/images/system_info.png)

- Displays system resource usage
- Shows active network interfaces
- Provides details on network configurations

### 📊 Connected Clients Page

![Connected Clients](https://github.com/BlackCat-443/Network-Guardian/blob/main/images/connected_clients.png?raw=true)

- Lists all currently connected devices
- Displays hostname, IP, and MAC addresses
- Shows active bandwidth usage

###  Netcut Conrol

![Connected Clients](https://github.com/BlackCat-443/Network-Guardian/blob/main/images/CutInform.png?raw=true)

## 🔧 NetCut Control Features (Under Development)

### ⚠️ **Status: Research & Development Phase**
**Current Status:** The NetCut features are currently in active development and research phase. These features are not yet ready for production use and may not function as expected.

### 🔬 **Features Under Research:**

#### 1. **Device Blocking Engine** 🔒
- **Technology Stack:** ARP Spoofing + iptables firewall integration
- **Current State:** Basic prototype implemented, requires optimization
- **Research Areas:**
  - Cross-platform ARP spoofing techniques
  - Persistent blocking mechanisms
  - Detection evasion methods
  - Performance impact analysis

#### 2. **Temporary Kick Function** 👢
- **Concept:** Temporarily disconnect devices for configurable time periods
- **Development Phase:** Algorithm design and testing
- **Technical Challenges:**
  - Reliable timing mechanisms
  - Automatic restoration procedures
  - Network state preservation

#### 3. **Network Traffic Interception** 📡
- **Research Goal:** Advanced traffic analysis and filtering
- **Current Focus:** Packet capture and analysis libraries
  - **Scapy** integration for packet manipulation
  - **PyShark** for high-level packet analysis
  - **DPDK** for high-performance packet processing (future)

### 🛠️ **Technical Implementation Roadmap:**

#### **Phase 1: Research & Prototyping** (Current)
- ✅ Basic ARP spoofing proof-of-concept
- ⚠️ iptables rule management system
- 🔄 Cross-platform compatibility testing
- 📊 Performance benchmarking

#### **Phase 2: Core Development** (Planned)
- 🔄 Stable blocking/kicking mechanisms
- 🔄 User interface integration
- 🔄 Configuration management system
- 🔄 Logging and monitoring

#### **Phase 3: Advanced Features** (Future)
- 🔄 Smart detection algorithms
- 🔄 Scheduled blocking rules
- 🔄 Network health monitoring
- 🔄 API for external integration

### 🧪 **Testing Framework Under Development:**

#### **Laboratory Testing Environment:**


## 📦 Requirements

Listed in `requirements.txt`:

```txt
flask==2.3.3
psutil==5.9.5
python-nmap==0.7.1
netifaces==0.11.0
Werkzeug==3.0.1
click==8.1.7
itsdangerous==2.1.2
Jinja2==3.1.2
MarkupSafe==2.1.3
requests==2.31.0
python-dotenv==1.0.0
scapy==2.5.0
```

Make sure you also have the `nmap` tool installed on your system (not just the Python library).  
Install `nmap` via:

- **Ubuntu/Debian**:
  ```bash
  sudo apt install nmap
  ```
- **Windows**: [Download from https://nmap.org/download.html](https://nmap.org/download.html)

## 🛡️ How It Works

### Device Blocking *(Still in Development)*

Network Guardian plans to use different methods based on your operating system:

- **Linux**: Uses iptables or arptables to block traffic from specified devices
- **Windows**: Creates Windows Firewall rules to block inbound and outbound connections

### Device Kicking *(Still in Development)*

- **Linux**: Uses ARP spoofing techniques to temporarily disconnect target devices
- **Windows**: Temporarily blocks and then unblocks devices after a short period



### Feature Running *(Still in Development)*

1. **REAL-TIME NETWORK SCANNER** - Deteksi semua device di jaringan
   - ARP table scanning
   - IP neighbor detection  
   - Fast ping detection
   - Auto-scan setiap 10 detik

2. **NETCUT ENGINE (FULLY WORKING)** - Block/kick devices seperti NetCut asli
   - ✅ **BLOCK DEVICE** - Potong koneksi internet permanen
   - ✅ **KICK DEVICE** - Temporary block (30 detik)
   - ✅ **RESTORE** - Kembalikan koneksi
   - ✅ **ARP SPOOFING** + iptables firewall
   - ✅ **Multi-threaded** ARP poisoning

3. **WEB DASHBOARD** - Interface lengkap
   - Real-time device list dengan IP, MAC, hostname
   - Network statistics & traffic monitoring
   - System information
   - One-click controls untuk block/unblock/kick

4. **API ENDPOINTS** - Untuk integrasi
   - REST API lengkap
   - WebSocket untuk real-time updates
   - Debug endpoints untuk troubleshooting


## MANUAL TESTING 

```bash

# Test scanner directly:
sudo ./venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from app import scan_fast
devices = scan_fast()
print(f'Found {len(devices)} devices')
for d in devices:
    if not d['is_local']:
        print(f\"  {d['ip']:15} {d['hostname']:20} {d['mac']}\")
"

# Check ARP table:
arp -n

# Test blocking manually:
curl -X POST http://localhost:8686/api/block-device \\
  -H \"Content-Type: application/json\" \\
  -d '{\"identifier\": \"192.168.1.100\"}'
```


## 🔒 Security Considerations

This tool is intended for use on networks you own or have permission to monitor. Using Network Guardian on unauthorized networks may violate local laws and regulations.

## 📌 Author

**Banh_Code** - Creator and Developer of Network Guardian

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

If you have any questions or need help, please open an issue in the GitHub repository.

## 💾 Download

[**💾 Download Network Guardian**](https://github.com/BlackCat-443/Network-Guardian.git/releases/latest)


