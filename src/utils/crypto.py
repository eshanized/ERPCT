#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crypto utilities for ERPCT.
This module provides cryptographic functions for password hashing and verification.
"""

import hashlib
import base64
import os
import binascii
from typing import Optional, Union, Tuple

import crypt
try:
    import bcrypt
except ImportError:
    bcrypt = None

def hash_password(password: str, hash_type: str, reference_hash: Optional[str] = None) -> str:
    """Hash a password using the specified hash type.
    
    Args:
        password: The password to hash
        hash_type: The hash algorithm to use (md5, sha1, sha256, sha512, md5crypt, bcrypt, etc.)
        reference_hash: A reference hash string, used for extracting salt for crypt-type hashes
        
    Returns:
        The hashed password as a string
    
    Raises:
        ValueError: If the hash type is not supported or arguments are invalid
    """
    if not password:
        raise ValueError("Password cannot be empty")
        
    if not hash_type:
        raise ValueError("Hash type must be specified")
        
    # Normalize hash type to lowercase
    hash_type = hash_type.lower()
    
    # Standard hash functions (no salt)
    if hash_type == "md5":
        return hashlib.md5(password.encode()).hexdigest()
    elif hash_type == "sha1":
        return hashlib.sha1(password.encode()).hexdigest()
    elif hash_type == "sha256":
        return hashlib.sha256(password.encode()).hexdigest()
    elif hash_type == "sha512":
        return hashlib.sha512(password.encode()).hexdigest()
    elif hash_type == "ntlm":
        # NTLM hash (commonly used in Windows environments)
        try:
            import hashlib
            hash_obj = hashlib.new('md4', password.encode('utf-16le'))
            return hash_obj.hexdigest()
        except (ImportError, ValueError):
            raise ValueError("NTLM hash type requires md4 support in hashlib")
    
    # Salted hash functions (crypt style)
    elif hash_type in ["md5crypt", "sha256crypt", "sha512crypt"]:
        if not reference_hash:
            # Generate new hash with random salt
            if hash_type == "md5crypt":
                return crypt.crypt(password, salt=crypt.METHOD_MD5)
            elif hash_type == "sha256crypt":
                return crypt.crypt(password, salt=crypt.METHOD_SHA256)
            elif hash_type == "sha512crypt":
                return crypt.crypt(password, salt=crypt.METHOD_SHA512)
        else:
            # Use salt from reference hash
            return crypt.crypt(password, salt=reference_hash)
            
    # BCrypt hash
    elif hash_type == "bcrypt":
        if not bcrypt:
            raise ValueError("BCrypt hash type requires bcrypt package")
            
        if not reference_hash:
            # Generate new hash with random salt
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode(), salt).decode()
        else:
            # Use salt from reference hash
            return bcrypt.hashpw(password.encode(), reference_hash.encode()).decode()
    
    # Base64-encoded hash (common in some web applications)
    elif hash_type == "base64":
        if hash_type == "base64md5":
            hash_bytes = hashlib.md5(password.encode()).digest()
        elif hash_type == "base64sha1":
            hash_bytes = hashlib.sha1(password.encode()).digest()
        else:  # Default to SHA-256
            hash_bytes = hashlib.sha256(password.encode()).digest()
            
        return base64.b64encode(hash_bytes).decode()
        
    # Hash with custom salt
    elif hash_type in ["md5salt", "sha1salt", "sha256salt", "sha512salt"]:
        # Extract or generate salt
        salt = ""
        if reference_hash and ":" in reference_hash:
            parts = reference_hash.split(":")
            if len(parts) >= 2:
                salt = parts[0]
                
        if not salt:
            # Generate random salt if not extracted from reference
            salt = binascii.hexlify(os.urandom(8)).decode()
            
        # Hash with salt prepended
        salted = (salt + password).encode()
        
        if hash_type == "md5salt":
            hashed = hashlib.md5(salted).hexdigest()
        elif hash_type == "sha1salt":
            hashed = hashlib.sha1(salted).hexdigest()
        elif hash_type == "sha256salt":
            hashed = hashlib.sha256(salted).hexdigest()
        elif hash_type == "sha512salt":
            hashed = hashlib.sha512(salted).hexdigest()
            
        # Return salt:hash format
        return f"{salt}:{hashed}"
        
    else:
        raise ValueError(f"Unsupported hash type: {hash_type}")

def verify_password(password: str, hash_str: str, hash_type: str) -> bool:
    """Verify a password against a hash.
    
    Args:
        password: The password to verify
        hash_str: The hash string to compare against
        hash_type: The hash algorithm used
        
    Returns:
        True if the password matches the hash, False otherwise
    """
    try:
        # Generate hash from password
        generated_hash = hash_password(password, hash_type, hash_str)
        
        # Compare hashes
        if hash_type.endswith("salt"):
            # For custom salt format, compare only the hash part
            if ":" in generated_hash and ":" in hash_str:
                generated_parts = generated_hash.split(":", 1)
                hash_parts = hash_str.split(":", 1)
                
                if len(generated_parts) >= 2 and len(hash_parts) >= 2:
                    return generated_parts[1] == hash_parts[1]
        
        # For standard hashes, compare the full string
        # For crypt-style hashes like bcrypt, the comparison needs to be exact
        if hash_type in ["md5", "sha1", "sha256", "sha512", "ntlm"]:
            return generated_hash.lower() == hash_str.lower()
        else:
            return generated_hash == hash_str
            
    except Exception:
        # If any error occurs during verification, return False
        return False

def generate_hash(password: str, hash_type: str, salt: Optional[str] = None) -> str:
    """Generate a new password hash.
    
    This is a convenience function to generate new password hashes
    for storing in a database or configuration file.
    
    Args:
        password: The password to hash
        hash_type: The hash algorithm to use
        salt: Optional salt to use (for some hash types)
        
    Returns:
        The generated hash string
    """
    if salt and hash_type.endswith("salt"):
        # For custom salt format
        salted = (salt + password).encode()
        
        if hash_type == "md5salt":
            hashed = hashlib.md5(salted).hexdigest()
        elif hash_type == "sha1salt":
            hashed = hashlib.sha1(salted).hexdigest()
        elif hash_type == "sha256salt":
            hashed = hashlib.sha256(salted).hexdigest()
        elif hash_type == "sha512salt":
            hashed = hashlib.sha512(salted).hexdigest()
            
        return f"{salt}:{hashed}"
    else:
        # For other hash types, use the standard function
        return hash_password(password, hash_type)

def extract_salt_from_hash(hash_str: str, hash_type: str) -> Optional[str]:
    """Extract the salt from a hash string.
    
    Args:
        hash_str: The hash string
        hash_type: The hash algorithm used
        
    Returns:
        The extracted salt, or None if not applicable
    """
    if not hash_str:
        return None
        
    if hash_type.endswith("salt") and ":" in hash_str:
        # For custom salt format, salt is before the colon
        return hash_str.split(":", 1)[0]
        
    elif hash_type in ["md5crypt", "sha256crypt", "sha512crypt"]:
        # For crypt-style hashes, the whole string is needed for salting
        return hash_str
        
    elif hash_type == "bcrypt" and hash_str.startswith("$2"):
        # For bcrypt, the whole string is needed for salting
        return hash_str
        
    # No salt for standard hashes
    return None

def analyze_hash(hash_str: str) -> Tuple[str, Optional[str]]:
    """Analyze a hash string to determine its type and extract salt if applicable.
    
    Args:
        hash_str: The hash string to analyze
        
    Returns:
        A tuple of (hash_type, salt)
    """
    if not hash_str:
        return ("unknown", None)
        
    # Check for crypt-style hashes first
    if hash_str.startswith("$1$"):
        return ("md5crypt", hash_str)
    elif hash_str.startswith("$5$"):
        return ("sha256crypt", hash_str)
    elif hash_str.startswith("$6$"):
        return ("sha512crypt", hash_str)
    elif hash_str.startswith("$2a$") or hash_str.startswith("$2b$"):
        return ("bcrypt", hash_str)
        
    # Check for salted hash format
    if ":" in hash_str:
        parts = hash_str.split(":", 1)
        if len(parts) == 2:
            salt, hash_part = parts
            
            # Try to determine hash type from hash part length
            hash_length = len(hash_part)
            
            if hash_length == 32:
                return ("md5salt", salt)
            elif hash_length == 40:
                return ("sha1salt", salt)
            elif hash_length == 64:
                return ("sha256salt", salt)
            elif hash_length == 128:
                return ("sha512salt", salt)
                
    # Check for standard hashes
    hash_length = len(hash_str)
    
    if hash_length == 32:
        return ("md5", None)
    elif hash_length == 40:
        return ("sha1", None)
    elif hash_length == 64:
        return ("sha256", None)
    elif hash_length == 128:
        return ("sha512", None)
        
    # Unknown hash type
    return ("unknown", None) 