# [file name]: router_scanner.py
"""
ROUTER EXPLOITATION TOOL - WiFi Client Scanner
Mendapatkan data hostname dan MAC address semua client yang terhubung ke router
Mirip dengan aplikasi WifiMan di Android
"""

import requests
import socket
import netifaces
import subprocess
import os
import re
import json
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
import hashlib
import base64

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RouterScanner:
    def __init__(self):
        print("\n" + "="*70)
        print("📡 ROUTER EXPLOITATION TOOL - WiFi Client Scanner")
        print("="*70)
        print("Mendapatkan data hostname & MAC address semua client")
        print("(Seperti aplikasi WifiMan di Android)")
        print("="*70)
        
        self.local_ip = self._get_local_ip()
        self.gateway_ip = self._get_gateway_ip()
        self.gateway_mac = self._get_gateway_mac()
        self.router_brand = None
        self.router_model = None
        self.router_firmware = None
        self.credentials = []
        self.devices = []
        self.vulnerabilities = []
        
        print(f"📍 Local IP: {self.local_ip}")
        print(f"🚪 Gateway IP: {self.gateway_ip}")
        print(f"🔑 Gateway MAC: {self.gateway_mac}")
        print("="*70)
    
    def _get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def _get_gateway_ip(self):
        """Get gateway IP address"""
        try:
            gateways = netifaces.gateways()
            return gateways['default'][netifaces.AF_INET][0]
        except:
            # Try to get from route
            try:
                result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'default' in line:
                        return line.split()[2]
            except:
                pass
            return "192.168.1.1"
    
    def _get_gateway_mac(self):
        """Get gateway MAC address"""
        try:
            # Try ARP table
            cmd = f"arp -n {self.gateway_ip} 2>/dev/null | grep -v Address | awk '{{print $3}}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            
            # Try ip neigh
            cmd = f"ip neigh show {self.gateway_ip} 2>/dev/null | awk '{{print $5}}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass
        return "Unknown"
    
    # ==================== ROUTER DETECTION ====================
    
    def detect_router(self):
        """Detect router brand, model, and firmware"""
        print("\n🔍 Mendeteksi informasi router...")
        
        # Try to access router web interface
        try:
            response = requests.get(f"http://{self.gateway_ip}", timeout=5, verify=False)
            
            # Check headers
            server = response.headers.get('Server', '')
            www_auth = response.headers.get('WWW-Authenticate', '')
            
            print(f"   HTTP Server: {server}")
            
            # Detect brand from server header
            if 'tp-link' in server.lower() or 'tp-link' in response.text.lower():
                self.router_brand = 'TP-Link'
                print(f"   ✅ Terdeteksi: TP-Link Router")
            elif 'd-link' in server.lower() or 'd-link' in response.text.lower():
                self.router_brand = 'D-Link'
                print(f"   ✅ Terdeteksi: D-Link Router")
            elif 'asus' in server.lower() or 'asus' in response.text.lower():
                self.router_brand = 'ASUS'
                print(f"   ✅ Terdeteksi: ASUS Router")
            elif 'netgear' in server.lower() or 'netgear' in response.text.lower():
                self.router_brand = 'Netgear'
                print(f"   ✅ Terdeteksi: Netgear Router")
            elif 'cisco' in server.lower() or 'cisco' in response.text.lower():
                self.router_brand = 'Cisco'
                print(f"   ✅ Terdeteksi: Cisco Router")
            elif 'mikrotik' in server.lower() or 'mikrotik' in response.text.lower():
                self.router_brand = 'MikroTik'
                print(f"   ✅ Terdeteksi: MikroTik Router")
            elif 'huawei' in server.lower() or 'huawei' in response.text.lower():
                self.router_brand = 'Huawei'
                print(f"   ✅ Terdeteksi: Huawei Router")
            elif 'zte' in server.lower() or 'zte' in response.text.lower():
                self.router_brand = 'ZTE'
                print(f"   ✅ Terdeteksi: ZTE Router")
            else:
                print(f"   ⚠️ Brand tidak dikenal")
            
            # Extract model from page title
            title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1)
                print(f"   📄 Page Title: {title}")
                
                # Try to extract model
                model_match = re.search(r'([A-Z0-9\-_]{5,20})', title)
                if model_match:
                    self.router_model = model_match.group(1)
                    print(f"   📦 Model: {self.router_model}")
            
        except Exception as e:
            print(f"   ❌ Gagal mengakses router: {e}")
        
        return self.router_brand
    
    # ==================== BRAND-SPECIFIC EXPLOITS ====================
    
    def exploit_tplink(self):
        """Exploit TP-Link routers"""
        print("\n📡 Mengeksploitasi TP-Link router...")
        
        endpoints = [
            '/userRpm/AssignedIpAddrListRpm.htm',
            '/userRpm/AssignedIpAddrListRpm.htm?t=',
            '/userRpm/WlanStationRpm.htm',
            '/userRpm/WlanStationRpm.htm?t=',
            '/userRpm/SystemStatisticRpm.htm',
            '/userRpm/SystemStatisticRpm.htm?t=',
            '/dhcpLease.htm',
            '/cgi-bin/luci/admin/status/dhcp',
            '/status/dhcp.html'
        ]
        
        # Try default credentials if needed
        creds = [('admin', 'admin'), ('admin', 'password'), ('admin', '1234')]
        
        for endpoint in endpoints:
            url = f"http://{self.gateway_ip}{endpoint}"
            
            try:
                # Try without auth first
                response = requests.get(url, timeout=5, verify=False)
                
                if response.status_code == 200:
                    devices = self._parse_tplink_dhcp(response.text)
                    if devices:
                        self.devices.extend(devices)
                        print(f"   ✅ Found {len(devices)} devices via {endpoint}")
                        self._print_devices(devices)
                        
                        # Check if vulnerable
                        self.vulnerabilities.append({
                            'type': 'information_disclosure',
                            'url': url,
                            'description': f'DHCP client list accessible without auth'
                        })
                
                # Try with auth
                elif response.status_code == 401:
                    for username, password in creds:
                        auth = requests.auth.HTTPBasicAuth(username, password)
                        response = requests.get(url, auth=auth, timeout=5, verify=False)
                        
                        if response.status_code == 200:
                            devices = self._parse_tplink_dhcp(response.text)
                            if devices:
                                self.devices.extend(devices)
                                print(f"   ✅ Found {len(devices)} devices via {endpoint} (auth: {username}:{password})")
                                self._print_devices(devices)
                                
                                self.vulnerabilities.append({
                                    'type': 'default_credentials',
                                    'url': url,
                                    'username': username,
                                    'password': password,
                                    'description': f'Default credentials work'
                                })
                            break
                            
            except Exception as e:
                pass
    
    def _parse_tplink_dhcp(self, html):
        """Parse TP-Link DHCP client page"""
        devices = []
        
        # Pattern for TP-Link DHCP table
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
        
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            
            if len(cells) >= 3:
                # Clean HTML tags
                ip = re.sub(r'<[^>]+>', '', cells[0]).strip()
                mac = re.sub(r'<[^>]+>', '', cells[1]).strip()
                hostname = re.sub(r'<[^>]+>', '', cells[2]).strip()
                
                # Validate IP
                if self._is_valid_ip(ip) and self._is_valid_mac(mac):
                    device = {
                        'ip': ip,
                        'mac': mac.upper(),
                        'hostname': hostname if hostname else 'Unknown',
                        'vendor': self._get_vendor_from_mac(mac),
                        'source': 'tplink_dhcp',
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    }
                    devices.append(device)
        
        # Alternative pattern: javascript array
        if not devices:
            # Look for var dhcpList = [...]
            match = re.search(r'var\s+dhcpList\s*=\s*\[(.*?)\];', html, re.DOTALL)
            if match:
                items = match.group(1).split('],[')
                for item in items:
                    parts = re.findall(r'"([^"]*)"', item)
                    if len(parts) >= 3:
                        ip, mac, hostname = parts[0], parts[1], parts[2]
                        if self._is_valid_ip(ip) and self._is_valid_mac(mac):
                            device = {
                                'ip': ip,
                                'mac': mac.upper(),
                                'hostname': hostname,
                                'vendor': self._get_vendor_from_mac(mac),
                                'source': 'tplink_js',
                                'timestamp': datetime.now().strftime("%H:%M:%S")
                            }
                            devices.append(device)
        
        return devices
    
    def exploit_dlink(self):
        """Exploit D-Link routers"""
        print("\n📡 Mengeksploitasi D-Link router...")
        
        endpoints = [
            '/dhcpclients.htm',
            '/wlanclients.htm',
            '/cgi-bin/dhcpClients',
            '/cgi-bin/wlanClients',
            '/status/dhcp.html',
            '/status/client_info.html',
            '/lan_dhcpClients.asp',
            '/wireless/wlanClients.asp'
        ]
        
        for endpoint in endpoints:
            url = f"http://{self.gateway_ip}{endpoint}"
            
            try:
                response = requests.get(url, timeout=5, verify=False)
                
                if response.status_code == 200:
                    devices = self._parse_dlink_clients(response.text)
                    if devices:
                        self.devices.extend(devices)
                        print(f"   ✅ Found {len(devices)} devices via {endpoint}")
                        self._print_devices(devices)
            except:
                pass
    
    def _parse_dlink_clients(self, html):
        """Parse D-Link client page"""
        devices = []
        
        # Pattern: IP, MAC, Hostname
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
        
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            
            if len(cells) >= 3:
                ip = re.sub(r'<[^>]+>', '', cells[0]).strip()
                mac = re.sub(r'<[^>]+>', '', cells[1]).strip()
                hostname = re.sub(r'<[^>]+>', '', cells[2]).strip()
                
                if self._is_valid_ip(ip) and self._is_valid_mac(mac):
                    device = {
                        'ip': ip,
                        'mac': mac.upper(),
                        'hostname': hostname,
                        'vendor': self._get_vendor_from_mac(mac),
                        'source': 'dlink',
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    }
                    devices.append(device)
        
        return devices
    
    def exploit_asus(self):
        """Exploit ASUS routers"""
        print("\n📡 Mengeksploitasi ASUS router...")
        
        endpoints = [
            '/ajax_status.xml',
            '/ajax_status.asp',
            '/update_networkmap.asp',
            '/device-map/clients.xml',
            '/device-map/clients.json',
            '/cgi-bin/client_list',
            '/cgi-bin/client_list.asp',
            '/cgi-bin/client_list.json'
        ]
        
        for endpoint in endpoints:
            url = f"http://{self.gateway_ip}{endpoint}"
            
            try:
                response = requests.get(url, timeout=5, verify=False)
                
                if response.status_code == 200:
                    # Try XML format
                    if '.xml' in endpoint:
                        devices = self._parse_asus_xml(response.text)
                    # Try JSON format
                    elif '.json' in endpoint:
                        devices = self._parse_asus_json(response.text)
                    else:
                        devices = self._parse_asus_ajax(response.text)
                    
                    if devices:
                        self.devices.extend(devices)
                        print(f"   ✅ Found {len(devices)} devices via {endpoint}")
                        self._print_devices(devices)
            except:
                pass
    
    def _parse_asus_xml(self, xml):
        """Parse ASUS XML format"""
        devices = []
        
        # Find all client entries
        clients = re.findall(r'<client>(.*?)</client>', xml, re.DOTALL)
        
        for client in clients:
            ip = re.search(r'<ip>(.*?)</ip>', client)
            mac = re.search(r'<mac>(.*?)</mac>', client)
            name = re.search(r'<name>(.*?)</name>', client)
            
            if ip and mac:
                device = {
                    'ip': ip.group(1),
                    'mac': mac.group(1).upper(),
                    'hostname': name.group(1) if name else 'Unknown',
                    'vendor': self._get_vendor_from_mac(mac.group(1)),
                    'source': 'asus_xml',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                }
                devices.append(device)
        
        return devices
    
    def _parse_asus_json(self, json_str):
        """Parse ASUS JSON format"""
        devices = []
        
        try:
            data = json.loads(json_str)
            
            # Try different JSON structures
            if 'clients' in data:
                for client in data['clients']:
                    device = {
                        'ip': client.get('ip', 'Unknown'),
                        'mac': client.get('mac', 'Unknown').upper(),
                        'hostname': client.get('name', 'Unknown'),
                        'vendor': self._get_vendor_from_mac(client.get('mac', '')),
                        'source': 'asus_json',
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    }
                    if self._is_valid_ip(device['ip']):
                        devices.append(device)
        except:
            pass
        
        return devices
    
    def _parse_asus_ajax(self, html):
        """Parse ASUS AJAX response"""
        devices = []
        
        # Look for javascript array
        matches = re.findall(r'\["([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\]', html)
        
        for ip, mac, hostname in matches:
            if self._is_valid_ip(ip) and self._is_valid_mac(mac):
                device = {
                    'ip': ip,
                    'mac': mac.upper(),
                    'hostname': hostname,
                    'vendor': self._get_vendor_from_mac(mac),
                    'source': 'asus_ajax',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                }
                devices.append(device)
        
        return devices
    
    def exploit_netgear(self):
        """Exploit Netgear routers"""
        print("\n📡 Mengeksploitasi Netgear router...")
        
        endpoints = [
            '/DHCP.html',
            '/WLAN.html',
            '/cgi-bin/attached_devices',
            '/cgi-bin/attached_devices.cgi',
            '/cgi-bin/wireless_clients',
            '/cgi-bin/wireless_clients.cgi',
            '/data.json',
            '/status/device_info'
        ]
        
        for endpoint in endpoints:
            url = f"http://{self.gateway_ip}{endpoint}"
            
            try:
                response = requests.get(url, timeout=5, verify=False)
                
                if response.status_code == 200:
                    if 'attached_devices' in endpoint:
                        devices = self._parse_netgear_cgi(response.text)
                    else:
                        devices = self._parse_generic_table(response.text)
                    
                    if devices:
                        self.devices.extend(devices)
                        print(f"   ✅ Found {len(devices)} devices via {endpoint}")
                        self._print_devices(devices)
            except:
                pass
    
    def _parse_netgear_cgi(self, content):
        """Parse Netgear CGI output"""
        devices = []
        
        # Format: IP;MAC;HOSTNAME
        lines = content.strip().split('\n')
        
        for line in lines:
            parts = line.strip().split(';')
            if len(parts) >= 3:
                ip, mac, hostname = parts[0], parts[1], parts[2]
                
                if self._is_valid_ip(ip) and self._is_valid_mac(mac):
                    device = {
                        'ip': ip,
                        'mac': mac.upper(),
                        'hostname': hostname,
                        'vendor': self._get_vendor_from_mac(mac),
                        'source': 'netgear_cgi',
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    }
                    devices.append(device)
        
        return devices
    
    def exploit_mikrotik(self):
        """Exploit MikroTik routers"""
        print("\n📡 Mengeksploitasi MikroTik router...")
        
        endpoints = [
            '/dhcp/lease/print',
            '/interface/wireless/registration-table/print',
            '/ip/dhcp-server/lease/print',
            '/ip/arp/print',
            '/snapshot.json',
            '/snapshot.rsc'
        ]
        
        for endpoint in endpoints:
            url = f"http://{self.gateway_ip}{endpoint}"
            
            try:
                response = requests.get(url, timeout=5, verify=False)
                
                if response.status_code == 200:
                    devices = self._parse_mikrotik(response.text)
                    if devices:
                        self.devices.extend(devices)
                        print(f"   ✅ Found {len(devices)} devices via {endpoint}")
                        self._print_devices(devices)
            except:
                pass
    
    def _parse_mikrotik(self, content):
        """Parse MikroTik output"""
        devices = []
        
        # MikroTik format: address, mac-address, host-name
        lines = content.strip().split('\n')
        
        for line in lines:
            # Look for address=xxx mac-address=xx:xx host-name=yyy
            ip_match = re.search(r'address=(\d+\.\d+\.\d+\.\d+)', line)
            mac_match = re.search(r'mac-address=([0-9A-F:]{17})', line, re.IGNORECASE)
            host_match = re.search(r'host-name=([^\s]+)', line)
            
            if ip_match and mac_match:
                device = {
                    'ip': ip_match.group(1),
                    'mac': mac_match.group(1).upper(),
                    'hostname': host_match.group(1) if host_match else 'Unknown',
                    'vendor': self._get_vendor_from_mac(mac_match.group(1)),
                    'source': 'mikrotik',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                }
                devices.append(device)
        
        return devices
    
    # ==================== GENERIC EXPLOITS ====================
    
    def exploit_dhcp_lease(self):
        """Try to get DHCP lease file"""
        print("\n📡 Mencari DHCP lease file...")
        
        dhcp_paths = [
            '/dhcp_lease.html',
            '/dhcp_leases.htm',
            '/cgi-bin/dhcp_lease',
            '/dhcpLease.htm',
            '/dhcpclients.htm',
            '/status/dhcp.html',
            '/status/device_info/dhcp_lease',
            '/cgi-bin/dhcpLease',
            '/dhcpClients.htm'
        ]
        
        for path in dhcp_paths:
            url = f"http://{self.gateway_ip}{path}"
            
            try:
                response = requests.get(url, timeout=3, verify=False)
                
                if response.status_code == 200:
                    devices = self._parse_generic_table(response.text)
                    
                    if not devices:
                        devices = self._parse_dhcp_lease_raw(response.text)
                    
                    if devices:
                        self.devices.extend(devices)
                        print(f"   ✅ Found {len(devices)} devices via {path}")
                        self._print_devices(devices)
                        
                        self.vulnerabilities.append({
                            'type': 'information_disclosure',
                            'url': url,
                            'description': 'DHCP lease file exposed'
                        })
            except:
                pass
    
    def _parse_generic_table(self, html):
        """Parse generic HTML table for devices"""
        devices = []
        
        # Find all tables
        tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
        
        for table in tables:
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
            
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                
                ip = None
                mac = None
                hostname = None
                
                for cell in cells:
                    clean = re.sub(r'<[^>]+>', '', cell).strip()
                    
                    if self._is_valid_ip(clean):
                        ip = clean
                    elif self._is_valid_mac(clean):
                        mac = clean
                    elif clean and len(clean) < 50 and not hostname:
                        hostname = clean
                
                if ip and mac:
                    device = {
                        'ip': ip,
                        'mac': mac.upper(),
                        'hostname': hostname if hostname else 'Unknown',
                        'vendor': self._get_vendor_from_mac(mac),
                        'source': 'generic_table',
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    }
                    devices.append(device)
        
        return devices
    
    def _parse_dhcp_lease_raw(self, content):
        """Parse raw DHCP lease content"""
        devices = []
        
        # Pattern: IP MAC HOSTNAME
        lines = content.strip().split('\n')
        
        for line in lines:
            parts = line.strip().split()
            
            if len(parts) >= 2:
                ip = None
                mac = None
                hostname = None
                
                for part in parts:
                    if self._is_valid_ip(part):
                        ip = part
                    elif self._is_valid_mac(part):
                        mac = part
                    elif part and len(part) < 50:
                        hostname = part
                
                if ip and mac:
                    device = {
                        'ip': ip,
                        'mac': mac.upper(),
                        'hostname': hostname if hostname else 'Unknown',
                        'vendor': self._get_vendor_from_mac(mac),
                        'source': 'dhcp_raw',
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    }
                    devices.append(device)
        
        return devices
    
    def exploit_arp_table(self):
        """Try to get ARP table from router"""
        print("\n📡 Mencari ARP table...")
        
        arp_paths = [
            '/arp_table.html',
            '/arp.htm',
            '/cgi-bin/arp',
            '/arp_table',
            '/status/arp.html',
            '/cgi-bin/arptable',
            '/arp.json'
        ]
        
        for path in arp_paths:
            url = f"http://{self.gateway_ip}{path}"
            
            try:
                response = requests.get(url, timeout=3, verify=False)
                
                if response.status_code == 200:
                    devices = self._parse_arp_table(response.text)
                    
                    if devices:
                        self.devices.extend(devices)
                        print(f"   ✅ Found {len(devices)} devices via {path}")
                        self._print_devices(devices)
            except:
                pass
    
    def _parse_arp_table(self, content):
        """Parse ARP table"""
        devices = []
        
        # Pattern: IP MAC
        ip_mac_pairs = re.findall(r'(\d+\.\d+\.\d+\.\d+)[\s:]+([0-9A-Fa-f:]{17})', content)
        
        for ip, mac in ip_mac_pairs:
            if ip != self.gateway_ip:
                device = {
                    'ip': ip,
                    'mac': mac.upper(),
                    'hostname': 'Unknown',
                    'vendor': self._get_vendor_from_mac(mac),
                    'source': 'arp_table',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                }
                devices.append(device)
        
        return devices
    
    def exploit_wireless_clients(self):
        """Try to get wireless client list"""
        print("\n📱 Mencari wireless clients...")
        
        wireless_paths = [
            '/wireless_clients.html',
            '/wireless_client.htm',
            '/cgi-bin/get_wireless',
            '/wireless_client_list',
            '/userRpm/WlanStationRpm.htm',
            '/cgi-bin/wireless/client_list',
            '/status/wireless.html',
            '/wlanclients.htm',
            '/wireless/wlan_clients.json'
        ]
        
        for path in wireless_paths:
            url = f"http://{self.gateway_ip}{path}"
            
            try:
                response = requests.get(url, timeout=3, verify=False)
                
                if response.status_code == 200:
                    devices = self._parse_wireless_clients(response.text)
                    
                    if devices:
                        self.devices.extend(devices)
                        print(f"   ✅ Found {len(devices)} wireless clients via {path}")
                        self._print_devices(devices)
            except:
                pass
    
    def _parse_wireless_clients(self, content):
        """Parse wireless client list"""
        devices = []
        
        # Try table format
        devices.extend(self._parse_generic_table(content))
        
        # Try JSON format
        if not devices:
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    for client in data:
                        ip = client.get('ip') or client.get('IP')
                        mac = client.get('mac') or client.get('MAC')
                        hostname = client.get('hostname') or client.get('name')
                        
                        if ip and mac:
                            device = {
                                'ip': ip,
                                'mac': mac.upper(),
                                'hostname': hostname if hostname else 'Unknown',
                                'vendor': self._get_vendor_from_mac(mac),
                                'source': 'wireless_json',
                                'timestamp': datetime.now().strftime("%H:%M:%S")
                            }
                            devices.append(device)
            except:
                pass
        
        return devices
    
    # ==================== UTILITY FUNCTIONS ====================
    
    def _is_valid_ip(self, ip):
        """Check if string is valid IP"""
        if not ip:
            return False
        
        pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
        match = re.match(pattern, ip)
        
        if match:
            for octet in match.groups():
                if int(octet) > 255:
                    return False
            return True
        
        return False
    
    def _is_valid_mac(self, mac):
        """Check if string is valid MAC address"""
        if not mac:
            return False
        
        # Format: xx:xx:xx:xx:xx:xx
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac))
    
    def _get_vendor_from_mac(self, mac):
        """Get vendor from MAC OUI"""
        if not mac or mac == 'Unknown':
            return 'Unknown'
        
        # Common OUI database
        oui_db = {
            '00:0C:29': 'VMware',
            '00:50:56': 'VMware',
            '00:1A:11': 'Apple',
            '00:1B:63': 'Apple',
            '00:26:BB': 'Apple',
            '00:1D:4F': 'Apple',
            '00:1B:21': 'Intel',
            '00:26:B0': 'Intel',
            '00:24:8C': 'Dell',
            '00:1D:72': 'HP',
            '00:12:F0': 'TP-Link',
            '00:23:CD': 'Netgear',
            '00:18:4D': 'Cisco',
            '00:15:5D': 'Microsoft',
            '08:00:27': 'VirtualBox',
            '00:0E:35': 'Realtek',
            '00:13:46': 'D-Link',
            '00:1E:58': 'Samsung',
            '00:1C:C0': 'Huawei',
            '00:19:99': 'Toshiba',
            '00:21:6A': 'Linksys',
            '00:1B:DC': 'Sony',
            '00:1D:60': 'Acer',
            '00:1C:26': 'Lenovo',
            '00:1F:F3': 'Xiaomi',
            '00:9A:CD': 'Xiaomi',
            'F0:33:E5': 'ZTE',
            '60:AB:14': 'Xiaomi',
            'D8:0D:17': 'Huawei',
        }
        
        mac_prefix = mac[:8].upper()
        return oui_db.get(mac_prefix, 'Unknown')
    
    def _print_devices(self, devices, limit=10):
        """Print devices in table format"""
        for i, device in enumerate(devices[:limit]):
            status = "📱"
            print(f"      {status} {device['ip']:15} {device['hostname']:20} {device['mac']} [{device['vendor']}]")
        
        if len(devices) > limit:
            print(f"      ... and {len(devices)-limit} more devices")
    
    # ==================== ACTIVE SCANNING ====================
    
    def scan_arp_active(self):
        """Active ARP scanning using scapy"""
        print("\n📡 Active ARP scanning...")
        
        try:
            from scapy.all import ARP, Ether, srp
            
            # Get network range
            network_prefix = '.'.join(self.local_ip.split('.')[:3])
            
            # Create ARP request
            arp = ARP(pdst=f"{network_prefix}.0/24")
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether/arp
            
            # Send and receive
            result = srp(packet, timeout=3, verbose=0)[0]
            
            devices = []
            for sent, received in result:
                ip = received.psrc
                mac = received.hwsrc
                
                if ip != self.local_ip and ip != self.gateway_ip:
                    # Try to get hostname
                    hostname = 'Unknown'
                    try:
                        hostname = socket.gethostbyaddr(ip)[0].split('.')[0]
                    except:
                        pass
                    
                    device = {
                        'ip': ip,
                        'mac': mac.upper(),
                        'hostname': hostname,
                        'vendor': self._get_vendor_from_mac(mac),
                        'source': 'active_arp',
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    }
                    devices.append(device)
            
            if devices:
                self.devices.extend(devices)
                print(f"   ✅ Found {len(devices)} devices via active ARP scan")
                self._print_devices(devices)
            
        except Exception as e:
            print(f"   ❌ Active ARP scan failed: {e}")
    
    def scan_passive(self):
        """Passive scanning (listen to network traffic)"""
        print("\n👂 Passive scanning (listening)...")
        print("   (Butuh waktu untuk mengumpulkan data)")
        
        try:
            from scapy.all import sniff
            
            devices_found = {}
            
            def packet_handler(pkt):
                if pkt.haslayer(ARP):
                    # ARP packet
                    ip = pkt.psrc if pkt.psrc else pkt.pdst
                    mac = pkt.hwsrc if pkt.hwsrc else pkt.hwdst
                    
                    if ip and mac and ip != self.local_ip:
                        if ip not in devices_found:
                            devices_found[ip] = {
                                'ip': ip,
                                'mac': mac.upper(),
                                'hostname': 'Unknown',
                                'vendor': self._get_vendor_from_mac(mac),
                                'source': 'passive_arp'
                            }
            
            # Sniff for 5 seconds
            sniff(timeout=5, prn=packet_handler, store=0)
            
            if devices_found:
                devices = list(devices_found.values())
                self.devices.extend(devices)
                print(f"   ✅ Found {len(devices)} devices via passive scan")
                self._print_devices(devices)
            
        except Exception as e:
            print(f"   ❌ Passive scan failed: {e}")
    
    # ==================== MAIN EXECUTION ====================
    
    def run_all_exploits(self):
        """Run all exploitation methods"""
        print("\n" + "="*70)
        print("🚀 MEMULAI EXPLOITATION...")
        print("="*70)
        
        # Detect router brand
        brand = self.detect_router()
        
        # Run brand-specific exploits
        if brand == 'TP-Link':
            self.exploit_tplink()
        elif brand == 'D-Link':
            self.exploit_dlink()
        elif brand == 'ASUS':
            self.exploit_asus()
        elif brand == 'Netgear':
            self.exploit_netgear()
        elif brand == 'MikroTik':
            self.exploit_mikrotik()
        
        # Run generic exploits
        self.exploit_dhcp_lease()
        self.exploit_arp_table()
        self.exploit_wireless_clients()
        
        # Active scanning
        self.scan_arp_active()
        self.scan_passive()
        
        # Display results
        self.show_results()
        
        # Save to file
        self.save_results()
    
    def show_results(self):
        """Display all found devices"""
        print("\n" + "="*70)
        print("📊 HASIL SCAN - DEVICE DI JARINGAN")
        print("="*70)
        
        # Remove duplicates (by IP)
        unique_devices = {}
        for device in self.devices:
            ip = device['ip']
            if ip not in unique_devices:
                unique_devices[ip] = device
        
        devices_list = list(unique_devices.values())
        
        # Sort by IP
        devices_list.sort(key=lambda x: [int(part) for part in x['ip'].split('.')])
        
        print(f"\nTotal devices ditemukan: {len(devices_list)}")
        print("-" * 70)
        print(f"{'No':<4} {'IP Address':<15} {'Hostname':<20} {'MAC Address':<18} {'Vendor'}")
        print("-" * 70)
        
        for i, device in enumerate(devices_list, 1):
            print(f"{i:<4} {device['ip']:<15} {device['hostname']:<20} {device['mac']:<18} {device['vendor']}")
        
        print("-" * 70)
        
        # Show vulnerabilities found
        if self.vulnerabilities:
            print("\n⚠️ VULNERABILITIES FOUND:")
            for vuln in self.vulnerabilities:
                print(f"   • {vuln['type']}: {vuln['description']}")
                if 'url' in vuln:
                    print(f"     URL: {vuln['url']}")
    
    def save_results(self):
        """Save results to JSON file"""
        try:
            filename = f"router_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output = {
                'timestamp': datetime.now().isoformat(),
                'gateway': {
                    'ip': self.gateway_ip,
                    'mac': self.gateway_mac,
                    'brand': self.router_brand,
                    'model': self.router_model,
                    'firmware': self.router_firmware
                },
                'devices': self.devices,
                'vulnerabilities': self.vulnerabilities,
                'total_devices': len(self.devices)
            }
            
            with open(filename, 'w') as f:
                json.dump(output, f, indent=2)
            
            print(f"\n💾 Hasil disimpan ke: {filename}")
            
        except Exception as e:
            print(f"\n❌ Gagal menyimpan hasil: {e}")

# ==================== MAIN ====================

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     ROUTER EXPLOITATION TOOL - WiFi Client Scanner       ║
    ║         Seperti WifiMan di Android                       ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    scanner = RouterScanner()
    scanner.run_all_exploits()