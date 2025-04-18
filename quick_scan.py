#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quick network scan on a specific target
"""

import nmap
from datetime import datetime

def main():
    # Target IP
    target_ip = "185.146.167.201"
    
    # Common service ports to check
    common_ports = "22,23,25,80,443,3389"
    
    print(f"Quick scan of {target_ip} at {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 50)
    
    try:
        # Initialize scanner
        scanner = nmap.PortScanner()
        
        # Simple ping scan first to check if host is up
        print(f"Checking if {target_ip} is up...")
        ping_result = scanner.scan(target_ip, arguments='-sn')
        
        host_status = "down"
        if target_ip in scanner.all_hosts():
            host_status = scanner[target_ip].state()
        
        print(f"Host status: {host_status}")
        
        if host_status == "up":
            # Scan only specified ports with minimal options for speed
            print(f"Scanning common ports {common_ports}...")
            scanner.scan(target_ip, common_ports, '-T4 -sV')
            
            # Display results
            for proto in scanner[target_ip].all_protocols():
                print(f"\nProtocol: {proto}")
                
                ports = sorted(scanner[target_ip][proto].keys())
                for port in ports:
                    state = scanner[target_ip][proto][port]['state']
                    service = scanner[target_ip][proto][port]['name']
                    print(f"Port {port}/{proto}: {state} - {service}")
        
    except Exception as e:
        print(f"Error during scan: {str(e)}")
    
    print("-" * 50)
    print(f"Scan completed at {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main() 