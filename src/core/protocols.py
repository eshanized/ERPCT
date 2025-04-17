#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT protocols module.
This module defines the protocols that can be used for authentication attacks.
"""

from enum import Enum, auto
from typing import Dict, List, Any, Optional, Set, Tuple


class Protocol(Enum):
    """Enumeration of protocols supported by the application."""
    
    SSH = auto()
    FTP = auto()
    HTTP_BASIC = auto()
    HTTP_FORM = auto()
    HTTP_DIGEST = auto()
    SMTP = auto()
    POP3 = auto()
    IMAP = auto()
    TELNET = auto()
    SMB = auto()
    RDP = auto()
    LDAP = auto()
    MYSQL = auto()
    POSTGRES = auto()
    MSSQL = auto()
    ORACLE = auto()
    VNC = auto()
    
    @classmethod
    def get_description(cls, protocol) -> str:
        """Get a description of the protocol.
        
        Args:
            protocol: The protocol to describe
            
        Returns:
            Description string
        """
        descriptions = {
            cls.SSH: "Secure Shell remote access protocol",
            cls.FTP: "File Transfer Protocol",
            cls.HTTP_BASIC: "HTTP Basic Authentication",
            cls.HTTP_FORM: "HTTP Form-based Authentication",
            cls.HTTP_DIGEST: "HTTP Digest Authentication",
            cls.SMTP: "Simple Mail Transfer Protocol",
            cls.POP3: "Post Office Protocol v3",
            cls.IMAP: "Internet Message Access Protocol",
            cls.TELNET: "Telnet remote access protocol",
            cls.SMB: "Server Message Block file sharing protocol",
            cls.RDP: "Remote Desktop Protocol",
            cls.LDAP: "Lightweight Directory Access Protocol",
            cls.MYSQL: "MySQL database server",
            cls.POSTGRES: "PostgreSQL database server",
            cls.MSSQL: "Microsoft SQL Server",
            cls.ORACLE: "Oracle database server",
            cls.VNC: "Virtual Network Computing"
        }
        return descriptions.get(protocol, "Unknown protocol")
    
    @classmethod
    def get_default_port(cls, protocol) -> int:
        """Get the default port for a protocol.
        
        Args:
            protocol: The protocol to get the default port for
            
        Returns:
            Default port number
        """
        ports = {
            cls.SSH: 22,
            cls.FTP: 21,
            cls.HTTP_BASIC: 80,
            cls.HTTP_FORM: 80,
            cls.HTTP_DIGEST: 80,
            cls.SMTP: 25,
            cls.POP3: 110,
            cls.IMAP: 143,
            cls.TELNET: 23,
            cls.SMB: 445,
            cls.RDP: 3389,
            cls.LDAP: 389,
            cls.MYSQL: 3306,
            cls.POSTGRES: 5432,
            cls.MSSQL: 1433,
            cls.ORACLE: 1521,
            cls.VNC: 5900
        }
        return ports.get(protocol, 0)
    
    @classmethod
    def get_config_template(cls, protocol) -> Dict[str, Any]:
        """Get a configuration template for the protocol.
        
        Args:
            protocol: The protocol to get a template for
            
        Returns:
            Configuration dictionary template
        """
        base_template = {
            "host": "",
            "port": 0,  # Will be filled with default port
            "timeout": 10,
            "username": "",
            "password": ""
        }
        
        protocol_templates = {
            cls.SSH: {
                **base_template,
                "key_auth_enabled": False,
                "key_file": "",
                "auth_timeout": 5,
                "banner_timeout": 5,
                "allow_agent": False,
                "look_for_keys": False,
                "command": "",
                "command_timeout": 10
            },
            cls.FTP: {
                **base_template,
                "passive": True,
                "tls": False,
                "read_timeout": 5
            },
            cls.HTTP_BASIC: {
                **base_template,
                "url": "",
                "https": False,
                "user_agent": "Mozilla/5.0",
                "verify_ssl": True
            },
            cls.HTTP_FORM: {
                **base_template,
                "url": "",
                "form_url": "",
                "username_field": "username",
                "password_field": "password",
                "other_fields": {},
                "success_string": "",
                "failure_string": "",
                "https": False,
                "user_agent": "Mozilla/5.0",
                "verify_ssl": True,
                "follow_redirects": True
            },
            # Add other protocol configurations here
        }
        
        template = protocol_templates.get(protocol, base_template).copy()
        template["port"] = cls.get_default_port(protocol)
        return template
    
    @classmethod
    def requires_module(cls, protocol) -> Optional[str]:
        """Check if a protocol requires an additional Python module.
        
        Args:
            protocol: The protocol to check
            
        Returns:
            Module name if required, None otherwise
        """
        requirements = {
            cls.SSH: "paramiko",
            cls.HTTP_BASIC: "requests",
            cls.HTTP_FORM: "requests",
            cls.HTTP_DIGEST: "requests",
            cls.SMTP: "smtplib",  # Built-in
            cls.POP3: "poplib",  # Built-in
            cls.IMAP: "imaplib",  # Built-in
            cls.TELNET: "telnetlib",  # Built-in
            cls.SMB: "impacket",
            cls.RDP: "rdpy",
            cls.LDAP: "ldap3",
            cls.MYSQL: "mysql-connector-python",
            cls.POSTGRES: "psycopg2",
            cls.MSSQL: "pymssql",
            cls.ORACLE: "cx_Oracle",
            cls.VNC: "python-vnc-client"
        }
        return requirements.get(protocol)
    
    @classmethod
    def get_available_protocols(cls) -> List[Tuple['Protocol', str]]:
        """Get a list of available protocols with descriptions.
        
        Returns:
            List of tuples containing (protocol, description)
        """
        return [(p, cls.get_description(p)) for p in cls] 