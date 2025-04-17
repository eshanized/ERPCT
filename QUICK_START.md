# ERPCT Quick Start Guide

ERPCT (Enhanced Rapid Password Cracking Tool) is now fully functional! This guide will help you get started using the tool.

## Installation

1. Make sure you have Python 3.8+ installed
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. For the GUI, you need GTK3 and PyGObject. The application will attempt to install these automatically.

## Command Line Usage

The simplest way to test a single set of credentials is using the `test_single_password.py` script:

```bash
python test_single_password.py --target <hostname/IP> --protocol <protocol> --username <username> --password <password>
```

Example:
```bash
python test_single_password.py --target example.com --protocol ssh --username admin --password password123
```

To see available protocols:
```bash
python test_single_password.py --list-protocols
```

### Advanced Command Line Usage

For more advanced usage, use the full CLI interface:

```bash
python src/main.py --target <hostname/IP> --protocol <protocol> --username <username> --wordlist data/common_passwords.txt
```

## GUI Usage

To start the GUI:

```bash
python run_gui.py
```

The GUI provides several tabs for different functionality:
- **Dashboard**: Overview of current status and recent results
- **Target**: Configure target systems
- **Attack**: Set up attack parameters and credentials
- **Protocols**: Configure protocol-specific options
- **Results**: View and manage attack results

## Available Protocols

ERPCT supports multiple protocols including:
- SSH
- FTP
- HTTP/HTTPS (Basic and Digest authentication)
- Telnet
- POP3
- IMAP
- SMTP
- SMB
- MySQL
- PostgreSQL
- VNC
- LDAP
- RDP (Remote Desktop Protocol)

## Troubleshooting

If you encounter issues:

1. Check the log files in the project directory:
   - `erpct.log`: Main application log
   - `simple_erpct.log`: Simplified GUI log
   - `gui_debug.log`: GUI-specific debugging information

2. Make sure you have all the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. If the GUI doesn't start, try running the simplified version:
   ```bash
   python simple_erpct.py
   ```

4. For testing individual protocols, use the test script:
   ```bash
   python test_single_password.py --target example.com --protocol ssh --username test --password test --verbose
   ```

## Security Notice

This tool is intended for legal security testing and educational purposes only. Only use it on systems you own or have explicit permission to test. Unauthorized access to computer systems is illegal and unethical. 