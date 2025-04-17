#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telnet client class for ERPCT.
This is a simplified version of the telnetlib module that was removed in Python 3.13.
"""

import socket
import time
import select
import re
from typing import Optional, Tuple, List, Union, Any, Dict

class Telnet:
    """Telnet interface class.
    
    This class provides a basic interface to the Telnet protocol, primarily
    for authentication testing rather than interactive use.
    """
    
    def __init__(self, host: Optional[str] = None, port: int = 23, timeout: Optional[float] = None):
        """Constructor.
        
        Args:
            host: Host name or IP address
            port: Port number
            timeout: Connection timeout in seconds
        """
        self.debuglevel = 0
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.rawq = b''
        self.irawq = 0
        self.cookedq = b''
        self.eof = False
        self.iacseq = b''
        self.sb = 0
        self.sbdataq = b''
        
        # Telnet protocol characters
        self.IAC = bytes([255])  # Interpret As Command
        self.DONT = bytes([254])
        self.DO = bytes([253])
        self.WONT = bytes([252])
        self.WILL = bytes([251])
        self.SB = bytes([250])   # Subnegotiation Begin
        self.SE = bytes([240])   # Subnegotiation End
        
        if host:
            self.open(host, port, timeout)
    
    def open(self, host: str, port: int = 23, timeout: Optional[float] = None) -> None:
        """Connect to a host.
        
        Args:
            host: Host name or IP address
            port: Port number
            timeout: Connection timeout in seconds
        """
        self.eof = False
        if self.sock:
            self.sock.close()
        
        self.host = host
        self.port = port
        
        try:
            self.sock = socket.create_connection((host, port), timeout)
        except socket.timeout:
            raise socket.timeout("Connection timed out")
    
    def close(self) -> None:
        """Close the connection."""
        if self.sock:
            self.sock.close()
        self.sock = None
        self.eof = True
    
    def read_until(self, expected: bytes, timeout: Optional[float] = None) -> bytes:
        """Read until a given byte string is encountered or until timeout.
        
        Args:
            expected: String to look for in the incoming data
            timeout: Maximum time to wait (in seconds)
            
        Returns:
            The data read, including the expected string if found
        """
        if self.eof:
            return b''
            
        if timeout is not None:
            deadline = time.time() + timeout
        else:
            deadline = None
        
        found_size = len(expected)
        buf = bytearray()
        
        while True:
            # Check if we've received enough data
            if expected in buf:
                return bytes(buf)
            
            # Check timeout
            if deadline and time.time() >= deadline:
                break
            
            # Read more data
            if not self.sock:
                raise EOFError("Connection closed")
            
            # Set a read timeout for each individual read
            read_timeout = 1.0  # 1 second per read
            if deadline:
                read_timeout = min(read_timeout, deadline - time.time())
                if read_timeout <= 0:
                    break
            
            # Wait for data with select
            readable, _, _ = select.select([self.sock], [], [], read_timeout)
            if not readable:
                continue  # No data available, try again
            
            try:
                # Receive data (up to 1024 bytes)
                data = self.sock.recv(1024)
                if not data:
                    self.eof = True
                    raise EOFError("Connection closed")
                buf.extend(data)
            except (socket.timeout, ConnectionResetError):
                break
        
        return bytes(buf)
    
    def write(self, buffer: bytes) -> None:
        """Write data to the socket.
        
        Args:
            buffer: Data to send
        """
        if not self.sock:
            raise OSError("Connection closed")
            
        self.sock.sendall(buffer)
    
    def read_all(self) -> bytes:
        """Read all data until EOF.
        
        Returns:
            All data received
        """
        if self.eof:
            return b''
            
        buf = bytearray()
        while not self.eof:
            try:
                if not self.sock:
                    raise EOFError("Connection closed")
                
                # Wait for data with select (with a timeout)
                readable, _, _ = select.select([self.sock], [], [], 0.5)
                if not readable:
                    # No data available within timeout
                    break
                
                # Receive data (up to 1024 bytes)
                data = self.sock.recv(1024)
                if not data:
                    self.eof = True
                    break
                buf.extend(data)
            except (socket.timeout, ConnectionResetError):
                break
        
        return bytes(buf)
    
    def expect(self, patterns: List[Union[bytes, re.Pattern]], timeout: Optional[float] = None) -> Tuple[int, Any, bytes]:
        """Read until one of a list of patterns matches.
        
        Args:
            patterns: List of regular expressions or byte strings to match
            timeout: Maximum time to wait (in seconds)
            
        Returns:
            A tuple of the index of the matched pattern, the match object, and the data read
        """
        if self.eof:
            return (-1, None, b'')
            
        if timeout is not None:
            deadline = time.time() + timeout
        else:
            deadline = None
        
        # Compile patterns if they are byte strings
        compiled_patterns = []
        for pattern in patterns:
            if isinstance(pattern, bytes):
                compiled_patterns.append(re.compile(re.escape(pattern)))
            else:
                compiled_patterns.append(pattern)
        
        buf = bytearray()
        
        while True:
            # Check for matches in current buffer
            for i, pattern in enumerate(compiled_patterns):
                match = pattern.search(buf)
                if match:
                    return (i, match, bytes(buf))
            
            # Check timeout
            if deadline and time.time() >= deadline:
                break
            
            # Read more data
            if not self.sock:
                raise EOFError("Connection closed")
            
            # Set a read timeout for each individual read
            read_timeout = 1.0  # 1 second per read
            if deadline:
                read_timeout = min(read_timeout, deadline - time.time())
                if read_timeout <= 0:
                    break
            
            # Wait for data with select
            readable, _, _ = select.select([self.sock], [], [], read_timeout)
            if not readable:
                continue  # No data available, try again
            
            try:
                # Receive data (up to 1024 bytes)
                data = self.sock.recv(1024)
                if not data:
                    self.eof = True
                    break
                buf.extend(data)
            except (socket.timeout, ConnectionResetError):
                break
        
        return (-1, None, bytes(buf)) 