#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ERPCT - Enhanced Rapid Password Cracking Tool
Main application entry point for command line interface.
"""

import os
import sys
import argparse
import json
import time
from typing import Dict, List, Optional, Any

from src.core.attack import Attack, AttackResult
from src.protocols import protocol_registry
from src.utils.logging import configure_logging, get_logger


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="ERPCT - Enhanced Rapid Password Cracking Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Target options
    parser.add_argument('--target', help='Target hostname or IP address')
    parser.add_argument('--port', type=int, help='Target port')
    
    # Protocol options
    parser.add_argument('--protocol', help='Protocol to use (ssh, ftp, http-form, etc.)')
    parser.add_argument('--list-protocols', action='store_true', help='List available protocols')
    
    # Authentication options
    parser.add_argument('--username', help='Username to try')
    parser.add_argument('--password', help='Password to try (for single attempts)')
    parser.add_argument('--userlist', help='File containing usernames (one per line)')
    parser.add_argument('--wordlist', help='Password wordlist to use')
    
    # Attack options
    parser.add_argument('--threads', type=int, default=1, help='Number of concurrent threads')
    parser.add_argument('--delay', type=float, default=0, help='Delay between connection attempts (seconds)')
    parser.add_argument('--timeout', type=int, default=10, help='Connection timeout (seconds)')
    parser.add_argument('--username-first', action='store_true', default=True, 
                        help='Try all passwords for each username (default)')
    parser.add_argument('--password-first', action='store_false', dest='username_first', 
                        help='Try all usernames for each password')
    
    # Output options
    parser.add_argument('--output', help='Output file for results')
    parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--debug', action='store_true', help='Debug output')
    
    # Protocol-specific options will be added by each protocol module
    
    # Parse arguments
    args = parser.parse_args()
    
    # Logging level based on verbosity
    if args.debug:
        configure_logging(level="debug")
    elif args.verbose:
        configure_logging(level="info")
    else:
        configure_logging(level="warning")
    
    return args


def main() -> int:
    """Main application entry point.
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger(__name__)
    args = parse_args()
    
    # List available protocols and exit
    if args.list_protocols:
        protocols = protocol_registry.get_all_protocols()
        print("Available protocols:")
        for name, protocol_class in protocols.items():
            instance = protocol_class({})
            print(f"  {name}: {instance.__doc__ or 'No description'} (default port: {instance.default_port})")
        return 0
    
    # Check for required arguments
    if not args.target:
        print("Error: Target must be specified", file=sys.stderr)
        return 1
    
    if not args.protocol:
        print("Error: Protocol must be specified", file=sys.stderr)
        return 1
    
    if not args.username and not args.userlist:
        print("Error: Username or username list must be specified", file=sys.stderr)
        return 1
    
    if not args.password and not args.wordlist:
        print("Error: Password or wordlist must be specified", file=sys.stderr)
        return 1
    
    # Prepare attack configuration
    config = vars(args)
    
    # Remove None values
    config = {k: v for k, v in config.items() if v is not None}
    
    # Some renaming for consistency
    if 'userlist' in config:
        config['username_list'] = config.pop('userlist')
    
    # Check if protocol is supported
    try:
        protocol_class = protocol_registry.get_protocol(args.protocol)
    except ValueError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1
    
    # Create attack instance
    try:
        attack = Attack(config)
    except ValueError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1
    
    # Prepare for results
    results = []
    
    # Success callback
    def on_success(result: AttackResult) -> None:
        """Handle successful authentication."""
        credentials = f"{result.username}:{result.password}"
        print(f"[+] Success: {credentials}")
        results.append({
            "username": result.username,
            "password": result.password,
            "timestamp": result.timestamp,
            "message": result.message
        })
    
    # Status update
    def print_status() -> None:
        """Print attack status."""
        stats = attack.get_status()
        progress = stats["progress_percent"]
        speed = stats["attempts_per_second"]
        eta = stats["estimated_time_remaining"]
        successes = stats["successful_attempts"]
        
        # Format ETA
        eta_str = time.strftime("%H:%M:%S", time.gmtime(eta)) if eta > 0 else "00:00:00"
        
        print(f"Progress: {progress:.2f}% | Speed: {speed:.2f}/s | ETA: {eta_str} | Found: {successes}")
    
    # Register callbacks
    attack.set_on_success_callback(on_success)
    
    # Start attack
    try:
        print(f"Starting attack against {args.target} using {args.protocol} protocol")
        attack.start()
        
        # Monitor progress
        try:
            while attack.status.running:
                time.sleep(1.0)
                if args.verbose:
                    print_status()
        except KeyboardInterrupt:
            print("\nReceived interrupt, stopping attack...")
            attack.stop()
        
        # Wait for attack to finish
        while attack.status.running:
            time.sleep(0.1)
        
        # Print final status
        print_status()
        print(f"Attack completed. Found {len(results)} valid credentials.")
        
        # Save results to file if requested
        if args.output:
            try:
                with open(args.output, 'w') as f:
                    if args.json:
                        json.dump(results, f, indent=2)
                    else:
                        for result in results:
                            f.write(f"{result['username']}:{result['password']}\n")
                print(f"Results saved to {args.output}")
            except Exception as e:
                print(f"Error saving results: {str(e)}", file=sys.stderr)
                return 1
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
