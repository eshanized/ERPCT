#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Networking utilities for ERPCT.
This module provides network-related functions and classes.
"""

import os
import socket
import ipaddress
import time
import ssl
from typing import Dict, List, Optional, Tuple, Union, Any
from urllib.parse import urlparse
import concurrent.futures

from src.utils.logging import get_logger

logger = get_logger(__name__)


def is_valid_ip(ip: str) -> bool:
    """Check if a string is a valid IP address.
    
    Args:
        ip: IP address string to check
        
    Returns:
        True if valid IP address, False otherwise
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_valid_hostname(hostname: str) -> bool:
    """Check if a string is a valid hostname.
    
    Args:
        hostname: Hostname to check
        
    Returns:
        True if valid hostname, False otherwise
    """
    if len(hostname) > 255:
        return False
    
    if hostname[-1] == ".":
        hostname = hostname[:-1]
    
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def resolve_hostname(hostname: str) -> List[str]:
    """Resolve a hostname to IP addresses.
    
    Args:
        hostname: Hostname to resolve
        
    Returns:
        List of IP addresses as strings
        
    Raises:
        socket.gaierror: If hostname cannot be resolved
    """
    try:
        ip_list = []
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ip not in ip_list:
                ip_list.append(ip)
        return ip_list
    except socket.gaierror as e:
        logger.error(f"Failed to resolve hostname {hostname}: {str(e)}")
        raise


def get_local_ip() -> str:
    """Get the local IP address of the machine.
    
    Returns:
        Local IP address as string
    """
    try:
        # Create a socket to a common external server to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        # Fallback if external connection fails
        return socket.gethostbyname(socket.gethostname())


def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is open on a host.
    
    Args:
        host: Hostname or IP address
        port: Port number to check
        timeout: Socket timeout in seconds
        
    Returns:
        True if port is open, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def check_multiple_ports(host: str, ports: List[int], timeout: float = 1.0) -> Dict[int, bool]:
    """Check multiple ports on a host concurrently.
    
    Args:
        host: Hostname or IP address
        ports: List of port numbers to check
        timeout: Socket timeout in seconds
        
    Returns:
        Dictionary mapping port numbers to boolean (True if open)
    """
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(ports))) as executor:
        future_to_port = {
            executor.submit(is_port_open, host, port, timeout): port
            for port in ports
        }
        
        for future in concurrent.futures.as_completed(future_to_port):
            port = future_to_port[future]
            try:
                results[port] = future.result()
            except Exception as e:
                logger.error(f"Error checking port {port}: {str(e)}")
                results[port] = False
    
    return results


def scan_network(network: str, timeout: float = 0.5) -> Dict[str, bool]:
    """Scan a network for active hosts.
    
    Args:
        network: Network in CIDR notation (e.g., "192.168.1.0/24")
        timeout: Timeout for each host in seconds
        
    Returns:
        Dictionary mapping IP addresses to boolean (True if host is up)
    """
    try:
        # Parse network
        net = ipaddress.ip_network(network, strict=False)
        hosts = list(net.hosts())
        
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            future_to_ip = {
                executor.submit(is_host_up, str(ip), timeout): str(ip)
                for ip in hosts
            }
            
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    results[ip] = future.result()
                except Exception as e:
                    logger.error(f"Error scanning host {ip}: {str(e)}")
                    results[ip] = False
        
        return results
    except ValueError as e:
        logger.error(f"Invalid network format: {str(e)}")
        return {}


def is_host_up(host: str, timeout: float = 1.0) -> bool:
    """Check if a host is up using basic socket connection.
    
    Args:
        host: Hostname or IP address
        timeout: Timeout in seconds
        
    Returns:
        True if host is up, False otherwise
    """
    # Try to connect to a port that's likely to be filtered rather than closed (to ensure a timely response)
    common_ports = [80, 443, 22, 7]
    
    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
    
    # If no ports are open, try ICMP ping (requires root/admin)
    try:
        if os.name == "nt":  # Windows
            response = os.system(f"ping -n 1 -w {int(timeout*1000)} {host} > nul")
            return response == 0
        else:  # Linux/Unix
            response = os.system(f"ping -c 1 -W {int(timeout)} {host} > /dev/null 2>&1")
            return response == 0
    except:
        return False
    
    return False


def get_ssl_cert_info(hostname: str, port: int = 443) -> Dict[str, Any]:
    """Get SSL certificate information from a host.
    
    Args:
        hostname: Hostname to check
        port: Port number (default 443 for HTTPS)
        
    Returns:
        Dictionary with certificate information
        
    Raises:
        ssl.SSLError: If SSL certificate cannot be retrieved
        socket.error: If connection fails
    """
    try:
        context = ssl.create_default_context()
        conn = context.wrap_socket(
            socket.socket(socket.AF_INET),
            server_hostname=hostname
        )
        conn.settimeout(5.0)
        conn.connect((hostname, port))
        cert = conn.getpeercert()
        conn.close()
        
        # Extract and format certificate information
        result = {
            'subject': dict(x[0] for x in cert['subject']),
            'issuer': dict(x[0] for x in cert['issuer']),
            'version': cert['version'],
            'serialNumber': cert['serialNumber'],
            'notBefore': cert['notBefore'],
            'notAfter': cert['notAfter'],
        }
        
        if 'subjectAltName' in cert:
            result['subjectAltName'] = cert['subjectAltName']
        
        return result
    except Exception as e:
        logger.error(f"Error getting SSL certificate for {hostname}:{port}: {str(e)}")
        raise


def parse_url(url: str) -> Dict[str, str]:
    """Parse a URL into its components.
    
    Args:
        url: URL to parse
        
    Returns:
        Dictionary with URL components
    """
    parsed = urlparse(url)
    result = {
        'scheme': parsed.scheme,
        'netloc': parsed.netloc,
        'hostname': parsed.hostname or '',
        'port': parsed.port or {'http': 80, 'https': 443}.get(parsed.scheme, None),
        'path': parsed.path,
        'params': parsed.params,
        'query': parsed.query,
        'fragment': parsed.fragment,
        'username': parsed.username or '',
        'password': parsed.password or '',
    }
    return result


import re  # Import re module for is_valid_hostname function

# Export the functions
__all__ = [
    'is_valid_ip',
    'is_valid_hostname',
    'resolve_hostname',
    'get_local_ip',
    'is_port_open',
    'check_multiple_ports',
    'scan_network',
    'is_host_up',
    'get_ssl_cert_info',
    'parse_url',
]
