#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Password validation module for ERPCT.
This module handles the validation of password attempts against various authentication protocols.
"""

import time
import socket
import threading
import queue
from typing import Dict, List, Any, Optional, Callable, Tuple

from src.utils.logging import get_logger
from src.utils.crypto import hash_password

class PasswordValidator:
    """Password validator class.
    
    Handles the validation of password attempts against various authentication protocols
    including local hash validation, network authentication protocols, and API-based auth.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the password validator with configuration.
        
        Args:
            config: Dictionary containing validator configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        
        # Extract target information
        self.target_type = config.get("target_type", "hash")
        self.target = config.get("target", "")
        self.username = config.get("username", "")
        self.hash_type = config.get("hash_type", "")
        self.protocol = config.get("protocol", "")
        self.host = config.get("host", "")
        self.port = config.get("port", 0)
        self.timeout = config.get("timeout", 5)
        
        # Setup rate limiting
        self.rate_limit = config.get("rate_limit", 0)  # attempts per second
        self.concurrent_limit = config.get("concurrent_limit", 5)
        self._last_attempt_time = 0
        self._attempt_interval = 0 if self.rate_limit <= 0 else 1.0 / self.rate_limit
        
        # For network-based auth
        self.connection_pool = []
        self.connection_lock = threading.Lock()
        
        # For tracking attempts
        self.total_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
        
        # For non-blocking validation
        self.validation_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.worker_threads = []
        self.stop_workers = threading.Event()
        
        # Callbacks
        self.success_callback = None
        
        # Initialize based on target type
        self._initialize_validator()
    
    def _initialize_validator(self) -> None:
        """Initialize the validator based on target type."""
        self.logger.info(f"Initializing password validator for target type: {self.target_type}")
        
        if self.target_type == "hash":
            # Validate hash format
            if not self.target:
                self.logger.error("No hash target specified")
                raise ValueError("Hash target must be specified")
                
            if not self.hash_type:
                self.logger.warning("Hash type not specified, attempting to auto-detect")
                self.hash_type = self._detect_hash_type(self.target)
                
        elif self.target_type == "network":
            # Validate network settings
            if not self.protocol:
                self.logger.error("No protocol specified for network target")
                raise ValueError("Protocol must be specified for network targets")
                
            if not self.host:
                self.logger.error("No host specified for network target")
                raise ValueError("Host must be specified for network targets")
                
            if not self.port:
                self.logger.warning("No port specified, using default for protocol")
                self.port = self._get_default_port(self.protocol)
                
            # Initialize connection pool if needed
            if self.protocol in ["ssh", "ftp", "smtp", "imap"]:
                self._initialize_connection_pool()
                
        elif self.target_type == "api":
            # Validate API settings
            if not self.target:
                self.logger.error("No API endpoint specified")
                raise ValueError("API endpoint must be specified")
                
            # Import API client if needed
            try:
                from src.utils.api_client import APIClient
                self.api_client = APIClient(self.config)
            except ImportError:
                self.logger.error("API client module not found")
                raise ImportError("API client module required for API targets")
                
        else:
            self.logger.error(f"Unsupported target type: {self.target_type}")
            raise ValueError(f"Unsupported target type: {self.target_type}")
        
        # Start worker threads for non-blocking validation
        self._start_workers()
        
    def _start_workers(self) -> None:
        """Start worker threads for password validation."""
        self.stop_workers.clear()
        
        for i in range(self.concurrent_limit):
            thread = threading.Thread(
                target=self._validation_worker,
                name=f"validator-worker-{i}",
                daemon=True
            )
            thread.start()
            self.worker_threads.append(thread)
            
        self.logger.debug(f"Started {len(self.worker_threads)} validation worker threads")
    
    def _validation_worker(self) -> None:
        """Worker thread function for password validation."""
        while not self.stop_workers.is_set():
            try:
                # Get password from queue with timeout
                item = self.validation_queue.get(timeout=0.1)
                if item is None:
                    break
                    
                password, attempt_id = item
                
                # Perform validation
                result = self.validate_password(password)
                
                # Put result in result queue
                self.result_queue.put((password, result, attempt_id))
                
                # Mark task as done
                self.validation_queue.task_done()
                
            except queue.Empty:
                # Queue is empty, continue waiting
                continue
                
            except Exception as e:
                self.logger.error(f"Error in validation worker: {str(e)}")
                # Mark task as done even if there was an error
                try:
                    self.validation_queue.task_done()
                except:
                    pass
    
    def _detect_hash_type(self, hash_str: str) -> str:
        """Attempt to detect the hash type from the hash string.
        
        Args:
            hash_str: The hash string to analyze
            
        Returns:
            Detected hash type or 'unknown'
        """
        # Simple heuristics for common hash types
        hash_length = len(hash_str)
        
        if hash_length == 32:
            return "md5"
        elif hash_length == 40:
            return "sha1"
        elif hash_length == 64:
            return "sha256"
        elif hash_length == 128:
            return "sha512"
        elif hash_str.startswith("$1$"):
            return "md5crypt"
        elif hash_str.startswith("$2a$") or hash_str.startswith("$2b$"):
            return "bcrypt"
        elif hash_str.startswith("$6$"):
            return "sha512crypt"
        elif hash_str.startswith("$5$"):
            return "sha256crypt"
        
        return "unknown"
    
    def _get_default_port(self, protocol: str) -> int:
        """Get default port for a protocol.
        
        Args:
            protocol: Protocol name
            
        Returns:
            Default port number
        """
        default_ports = {
            "http": 80,
            "https": 443,
            "ftp": 21,
            "ssh": 22,
            "telnet": 23,
            "smtp": 25,
            "pop3": 110,
            "imap": 143,
            "ldap": 389,
            "smb": 445,
            "rdp": 3389
        }
        
        return default_ports.get(protocol.lower(), 0)
    
    def _initialize_connection_pool(self) -> None:
        """Initialize connection pool for network protocols."""
        self.logger.debug(f"Initializing connection pool for {self.protocol}")
        
        # For now, just pre-allocate connection objects
        # Actual connections are established during validation
        pool_size = min(self.concurrent_limit, 10)
        
        with self.connection_lock:
            self.connection_pool = [None] * pool_size
    
    def validate_password_async(self, password: str) -> int:
        """Queue a password for asynchronous validation.
        
        Args:
            password: Password to validate
            
        Returns:
            Attempt ID for tracking the result
        """
        # Generate attempt ID
        attempt_id = self.total_attempts
        self.total_attempts += 1
        
        # Add to validation queue
        self.validation_queue.put((password, attempt_id))
        
        return attempt_id
    
    def validate_password(self, password: str) -> bool:
        """Validate a password against the target.
        
        Args:
            password: Password to validate
            
        Returns:
            True if the password is valid, False otherwise
        """
        # Apply rate limiting if configured
        if self.rate_limit > 0:
            current_time = time.time()
            time_since_last = current_time - self._last_attempt_time
            
            if time_since_last < self._attempt_interval:
                # Sleep to enforce rate limit
                time.sleep(self._attempt_interval - time_since_last)
                
            self._last_attempt_time = time.time()
        
        # Dispatch to appropriate validation method
        if self.target_type == "hash":
            result = self._validate_hash(password)
        elif self.target_type == "network":
            result = self._validate_network(password)
        elif self.target_type == "api":
            result = self._validate_api(password)
        else:
            self.logger.error(f"Unsupported target type: {self.target_type}")
            result = False
        
        # Update statistics
        if result:
            self.successful_attempts += 1
            # Call success callback if registered
            if self.success_callback:
                try:
                    self.success_callback(password, self.username)
                except Exception as e:
                    self.logger.error(f"Error in success callback: {str(e)}")
        else:
            self.failed_attempts += 1
            
        return result
    
    def _validate_hash(self, password: str) -> bool:
        """Validate a password against a hash.
        
        Args:
            password: Password to validate
            
        Returns:
            True if the password matches the hash, False otherwise
        """
        try:
            # Hash the password using the specified hash type
            hashed_password = hash_password(password, self.hash_type, self.target)
            
            # For hash validation, we're often comparing to a stored hash
            if self.hash_type.endswith("crypt"):
                # crypt-style hashes include the salt, so we compare directly
                return hashed_password == self.target
            else:
                # Standard hashes, just compare the hash values
                return hashed_password.lower() == self.target.lower()
                
        except Exception as e:
            self.logger.error(f"Error validating hash: {str(e)}")
            return False
    
    def _validate_network(self, password: str) -> bool:
        """Validate a password against a network service.
        
        Args:
            password: Password to validate
            
        Returns:
            True if authentication succeeds, False otherwise
        """
        # Dispatch to protocol-specific validation method
        protocol = self.protocol.lower()
        
        try:
            if protocol == "ssh":
                return self._validate_ssh(password)
            elif protocol == "ftp":
                return self._validate_ftp(password)
            elif protocol == "smtp":
                return self._validate_smtp(password)
            elif protocol == "http" or protocol == "https":
                return self._validate_http(password)
            elif protocol == "rdp":
                return self._validate_rdp(password)
            elif protocol == "smb":
                return self._validate_smb(password)
            elif protocol == "ldap":
                return self._validate_ldap(password)
            else:
                self.logger.error(f"Unsupported protocol: {protocol}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating {protocol}: {str(e)}")
            return False
    
    def _validate_ssh(self, password: str) -> bool:
        """Validate SSH authentication.
        
        Args:
            password: Password to validate
            
        Returns:
            True if authentication succeeds, False otherwise
        """
        try:
            # Import paramiko only when needed
            import paramiko
            
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Attempt connection with timeout
            ssh_client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )
            
            # If we got here, authentication succeeded
            ssh_client.close()
            return True
            
        except paramiko.AuthenticationException:
            # Authentication failed
            return False
            
        except Exception as e:
            self.logger.error(f"SSH validation error: {str(e)}")
            return False
    
    def _validate_ftp(self, password: str) -> bool:
        """Validate FTP authentication.
        
        Args:
            password: Password to validate
            
        Returns:
            True if authentication succeeds, False otherwise
        """
        try:
            # Import ftplib only when needed
            import ftplib
            
            # Create FTP client and attempt login
            ftp = ftplib.FTP(timeout=self.timeout)
            ftp.connect(self.host, self.port)
            ftp.login(self.username, password)
            
            # If we got here, authentication succeeded
            ftp.quit()
            return True
            
        except ftplib.error_perm as e:
            # Authentication failed
            if "530" in str(e):  # Login incorrect
                return False
            else:
                self.logger.error(f"FTP error: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"FTP validation error: {str(e)}")
            return False
    
    def _validate_smtp(self, password: str) -> bool:
        """Validate SMTP authentication.
        
        Args:
            password: Password to validate
            
        Returns:
            True if authentication succeeds, False otherwise
        """
        try:
            # Import smtplib only when needed
            import smtplib
            
            # Create SMTP client and attempt login
            smtp = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            
            # Start TLS if available
            try:
                smtp.starttls()
            except:
                # TLS not supported, continue without it
                pass
                
            # Attempt authentication
            smtp.login(self.username, password)
            
            # If we got here, authentication succeeded
            smtp.quit()
            return True
            
        except smtplib.SMTPAuthenticationError:
            # Authentication failed
            return False
            
        except Exception as e:
            self.logger.error(f"SMTP validation error: {str(e)}")
            return False
    
    def _validate_http(self, password: str) -> bool:
        """Validate HTTP/HTTPS authentication.
        
        Args:
            password: Password to validate
            
        Returns:
            True if authentication succeeds, False otherwise
        """
        try:
            # Import requests only when needed
            import requests
            from requests.auth import HTTPBasicAuth, HTTPDigestAuth
            
            # Determine auth type (basic or digest)
            auth_type = self.config.get("auth_type", "basic")
            url = self.target  # URL should be in target field
            
            # Create appropriate auth object
            if auth_type.lower() == "digest":
                auth = HTTPDigestAuth(self.username, password)
            else:
                auth = HTTPBasicAuth(self.username, password)
                
            # Make request with timeout
            response = requests.get(
                url,
                auth=auth,
                timeout=self.timeout,
                verify=False  # Skip SSL verification
            )
            
            # Check if authentication was successful
            # Usually 200 OK indicates success, 401 indicates auth failure
            return response.status_code != 401
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"HTTP request error: {str(e)}")
            return False
            
        except Exception as e:
            self.logger.error(f"HTTP validation error: {str(e)}")
            return False
    
    def _validate_rdp(self, password: str) -> bool:
        """Validate RDP authentication.
        
        Args:
            password: Password to validate
            
        Returns:
            True if authentication succeeds, False otherwise
        """
        # RDP validation requires external tools
        # For now, use a dummy implementation
        self.logger.warning("RDP validation not fully implemented")
        return False
    
    def _validate_smb(self, password: str) -> bool:
        """Validate SMB authentication.
        
        Args:
            password: Password to validate
            
        Returns:
            True if authentication succeeds, False otherwise
        """
        try:
            # Import pysmb only when needed
            from smb.SMBConnection import SMBConnection
            
            # Try to determine client and server names
            client_name = socket.gethostname()
            server_name = self.config.get("server_name", "*SMBSERVER")
            domain = self.config.get("domain", "")
            
            # Create connection
            conn = SMBConnection(
                self.username,
                password,
                client_name,
                server_name,
                domain=domain,
                use_ntlm_v2=True
            )
            
            # Attempt connection with timeout
            is_connected = conn.connect(self.host, self.port, timeout=self.timeout)
            
            # Close connection if successful
            if is_connected:
                conn.close()
                
            return is_connected
            
        except Exception as e:
            self.logger.error(f"SMB validation error: {str(e)}")
            return False
    
    def _validate_ldap(self, password: str) -> bool:
        """Validate LDAP authentication.
        
        Args:
            password: Password to validate
            
        Returns:
            True if authentication succeeds, False otherwise
        """
        try:
            # Import ldap3 only when needed
            import ldap3
            
            # Determine bind DN (Distinguished Name)
            bind_dn = self.config.get("bind_dn", self.username)
            if not bind_dn and self.username:
                # Try to construct a simple bind DN from username
                bind_dn = f"cn={self.username},dc=example,dc=com"
                
            # Create server object
            server = ldap3.Server(
                self.host,
                port=self.port,
                use_ssl=self.config.get("use_ssl", False),
                connect_timeout=self.timeout
            )
            
            # Create connection
            conn = ldap3.Connection(
                server,
                user=bind_dn,
                password=password,
                auto_bind=ldap3.AUTO_BIND_NO_TLS
            )
            
            # Attempt to bind
            success = conn.bind()
            
            # Close connection
            conn.unbind()
            
            return success
            
        except Exception as e:
            self.logger.error(f"LDAP validation error: {str(e)}")
            return False
    
    def _validate_api(self, password: str) -> bool:
        """Validate authentication against a custom API.
        
        Args:
            password: Password to validate
            
        Returns:
            True if authentication succeeds, False otherwise
        """
        try:
            # Use API client to authenticate
            return self.api_client.authenticate(self.username, password)
            
        except Exception as e:
            self.logger.error(f"API validation error: {str(e)}")
            return False
    
    def get_results(self) -> Optional[Tuple[str, bool, int]]:
        """Get the next validation result if available.
        
        Returns:
            Tuple of (password, result, attempt_id) or None if no results
        """
        try:
            # Non-blocking get
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None
    
    def set_success_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback function for successful password validations.
        
        Args:
            callback: Function to call when a password is validated
                     Function should accept (password, username) as arguments
        """
        self.success_callback = callback
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics.
        
        Returns:
            Dictionary of validation statistics
        """
        return {
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "pending_attempts": self.validation_queue.qsize(),
            "success_rate": self.successful_attempts / max(1, self.total_attempts)
        }
    
    def shutdown(self) -> None:
        """Shutdown the validator and clean up resources."""
        self.logger.info("Shutting down password validator")
        
        # Stop worker threads
        self.stop_workers.set()
        
        # Put None in queue to signal workers to exit
        for _ in range(len(self.worker_threads)):
            try:
                self.validation_queue.put(None)
            except:
                pass
                
        # Wait for threads to finish
        for thread in self.worker_threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
                
        self.worker_threads = []
        
        # Close any open connections
        with self.connection_lock:
            for conn in self.connection_pool:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                        
            self.connection_pool = [] 