#!/usr/bin/env python3
"""
ERPCT - Enhanced Rapid Password Cracking Tool
Main entry point for the application
"""

import sys
import os
import argparse
import logging
from importlib import import_module

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='ERPCT - Enhanced Rapid Password Cracking Tool'
    )
    parser.add_argument('--gui', action='store_true', 
                        help='Launch with graphical user interface (default)')
    parser.add_argument('--target', type=str, help='Target to attack (hostname/IP or file with targets)')
    parser.add_argument('--protocol', type=str, help='Protocol to use for the attack')
    parser.add_argument('--port', type=int, help='Port number for the target')
    parser.add_argument('--username', type=str, help='Username to test')
    parser.add_argument('--username-list', type=str, help='File containing list of usernames')
    parser.add_argument('--wordlist', type=str, help='Wordlist to use for password attack')
    parser.add_argument('--threads', type=int, default=1, help='Number of concurrent threads')
    parser.add_argument('--delay', type=float, default=0, help='Delay between attempts in seconds')
    parser.add_argument('--timeout', type=int, default=30, help='Connection timeout in seconds')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Increase verbosity')
    
    # Advanced options
    advanced = parser.add_argument_group('Advanced options')
    advanced.add_argument('--rules', type=str, help='Rules file for password mutations')
    advanced.add_argument('--proxy', type=str, help='Proxy to use (format: type://host:port)')
    advanced.add_argument('--form-data', type=str, help='Form data for HTTP attacks')
    advanced.add_argument('--success-match', type=str, help='String to match for successful login')
    advanced.add_argument('--distributed', action='store_true', help='Enable distributed mode')
    advanced.add_argument('--coordinator', type=str, help='Coordinator address for distributed mode')
    
    return parser.parse_args()

def setup_logging(verbosity):
    """Configure logging based on verbosity level"""
    log_levels = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG
    }
    level = log_levels.get(verbosity, logging.DEBUG)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def main():
    """Main entry point for the application"""
    args = parse_arguments()
    setup_logging(args.verbose)
    
    # If no arguments or --gui specified, launch GUI
    if len(sys.argv) == 1 or args.gui:
        try:
            from src.gui.main_window import main as gui_main
            return gui_main()
        except ImportError as e:
            logging.error(f"Failed to start GUI: {e}")
            logging.error("Make sure GTK dependencies are installed")
            return 1
    
    # Otherwise run in CLI mode
    if not args.target or not args.protocol:
        logging.error("Target and protocol are required for CLI mode")
        return 1
    
    try:
        # Import the appropriate protocol module
        protocol_module = import_module(f'src.protocols.{args.protocol.lower()}')
        
        # Initialize the engine
        from src.core.engine import Engine
        engine = Engine()
        
        # Configure the attack
        engine.configure(args)
        
        # Run the attack
        engine.run()
        
        # Display results
        engine.show_results()
        
    except ImportError as e:
        logging.error(f"Protocol module not found: {e}")
        return 1
    except Exception as e:
        logging.error(f"Error during execution: {e}")
        if args.verbose >= 2:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
