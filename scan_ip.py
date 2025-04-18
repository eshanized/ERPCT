#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command-line utility to scan a specific IP address
"""

import sys
import os
import argparse
import nmap
import time
from datetime import datetime

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Scan a specific IP address for open ports and services")
    parser.add_argument("ip", help="IP address to scan")
    parser.add_argument("-p", "--ports", default="21-25,53,80,443,3306,3389,5432,8080,8443", 
                        help="Port range to scan (default: common ports)")
    parser.add_argument("-t", "--timing", type=int, choices=range(0, 6), default=4,
                        help="Timing template (0=slowest, 5=fastest)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Validate IP
    try:
        import socket
        socket.inet_aton(args.ip)
    except socket.error:
        print(f"Error: '{args.ip}' is not a valid IP address")
        return 1
    
    # Start scan
    start_time = datetime.now()
    print(f"Starting scan of {args.ip} at {start_time.strftime('%H:%M:%S')}")
    print(f"Ports: {args.ports}")
    print("-" * 60)
    
    # Create scanner
    scanner = nmap.PortScanner()
    
    try:
        # Run ping scan first to check if host is up
        print(f"Checking if {args.ip} is up...")
        ping_result = scanner.scan(args.ip, arguments='-sn')
        
        host_status = "down"
        if args.ip in scanner.all_hosts():
            host_status = scanner[args.ip].state()
        
        print(f"Host status: {host_status}")
        
        if host_status == "up" or args.verbose:
            # Run port scan
            print(f"Scanning ports...")
            
            # Set scan options
            scan_args = f"-T{args.timing} -Pn -sV"  # Skip ping, perform service detection
            
            if args.verbose:
                print(f"Running: nmap {scan_args} -p {args.ports} {args.ip}")
                
            scan_result = scanner.scan(args.ip, args.ports, scan_args)
            
            # Process results
            if args.ip in scanner.all_hosts():
                hostname = scanner[args.ip].hostname()
                if hostname:
                    print(f"Hostname: {hostname}")
                
                # Print open ports
                print("\nOpen ports:")
                print("-" * 60)
                print("PORT      STATE  SERVICE         VERSION")
                
                found_open_ports = False
                
                for proto in scanner[args.ip].all_protocols():
                    ports = sorted(scanner[args.ip][proto].keys())
                    
                    for port in ports:
                        state = scanner[args.ip][proto][port]['state']
                        
                        if state == 'open':
                            found_open_ports = True
                            service = scanner[args.ip][proto][port]['name']
                            product = scanner[args.ip][proto][port].get('product', '')
                            version = scanner[args.ip][proto][port].get('version', '')
                            
                            service_str = f"{service}"
                            
                            version_str = ""
                            if product:
                                version_str = product
                                if version:
                                    version_str += f" {version}"
                            
                            # Format the output to align columns
                            print(f"{port}/{proto:<6} {state:<6} {service:<15} {version_str}")
                
                if not found_open_ports:
                    print("No open ports found")
            else:
                print("Host was not found in scan results")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print("-" * 60)
        print(f"Scan completed at {end_time.strftime('%H:%M:%S')} (took {duration:.2f} seconds)")
        
        return 0
        
    except Exception as e:
        print(f"Error during scan: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 