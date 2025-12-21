#!/usr/bin/env python3
# test_cut.py
# Jalankan: sudo python3 test_cut.py <target_ip>

import sys
import subprocess
import time

def test_cut(target_ip):
    print(f"🔪 TESTING NETCUT FOR: {target_ip}")
    print("="*50)
    
    # 1. Test ping sebelum cut
    print("1. Testing ping BEFORE cut...")
    result = subprocess.run(['ping', '-c', '2', '-W', '1', target_ip], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("   ✅ Device is online (responds to ping)")
    else:
        print("   ❌ Device is offline or blocking ping")
    
    # 2. Test curl/HTTP sebelum cut
    print("\n2. Testing HTTP access BEFORE cut...")
    try:
        import requests
        response = requests.get(f"http://{target_ip}", timeout=3)
        print(f"   ✅ HTTP access: {response.status_code}")
    except:
        print("   ❌ No HTTP access")
    
    # 3. Cut internet
    print("\n3. Cutting internet...")
    # Panggil API NetCut atau langsung fungsi cut_internet
    import app
    success = app.netcut.cut_internet(target_ip)
    
    if success:
        print("   ✅ Internet cut command sent")
        
        # Tunggu 5 detik
        print("   ⏳ Waiting 5 seconds...")
        time.sleep(5)
        
        # 4. Test ping setelah cut
        print("\n4. Testing ping AFTER cut...")
        result = subprocess.run(['ping', '-c', '2', '-W', '1', target_ip], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ⚠️  Device still responds to ping (might be cached)")
        else:
            print("   ✅ Device does NOT respond to ping (GOOD!)")
        
        # 5. Check iptables rules
        print("\n5. Checking iptables rules...")
        result = subprocess.run(['iptables', '-L', '-n', '-v'], 
                              capture_output=True, text=True)
        
        if target_ip in result.stdout:
            print("   ✅ iptables DROP rules found")
        else:
            print("   ❌ No iptables rules found")
        
        # 6. Check ARP cache di local
        print("\n6. Checking local ARP cache...")
        result = subprocess.run(['arp', '-n'], capture_output=True, text=True)
        
        if target_ip in result.stdout:
            print("   ✅ Target in ARP cache")
            for line in result.stdout.splitlines():
                if target_ip in line:
                    print(f"   ARP entry: {line.strip()}")
        else:
            print("   ❌ Target not in ARP cache")
    
    else:
        print("   ❌ Failed to cut internet")
    
    print("="*50)
    print("Test complete!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sudo python3 test_cut.py <target_ip>")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    test_cut(target_ip)