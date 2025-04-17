# ERPCT - Enhanced Rapid Password Cracking Tool

ERPCT is an advanced password cracking tool with a GTK-based graphical user interface, designed as a more powerful and feature-rich alternative to traditional password cracking tools. It supports multiple authentication protocols and implements sophisticated attack strategies for security testing purposes.

## Features

- **Multi-Protocol Support**
  - Supports a wide range of protocols: SSH, FTP, HTTP/HTTPS, SMTP, Telnet, RDP, SMB, POP3, IMAP, LDAP, MySQL, PostgreSQL, VNC
  - Extensible architecture for custom protocol implementations

- **Intuitive GTK-based GUI**
  - Configuration Manager for editing system settings
  - Protocol Editor for managing authentication protocols
  - Dashboard with quick access to all features

- **Advanced Cracking Capabilities**
  - Dictionary attacks with customizable wordlists
  - Multi-threaded architecture for concurrent attempts
  - Configurable timing and evasion techniques

## Installation

### Prerequisites

- Python 3.8 or higher
- GTK 3 with PyGObject

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-dev libssl-dev
```

#### Fedora
```bash
sudo dnf install python3-gobject python3-cairo-devel gtk3 python3-devel openssl-devel
```

#### macOS
```bash
brew install pygobject3 gtk+3 python cairo
```

#### Windows
Windows users should use [MSYS2](https://www.msys2.org/) to install GTK:
```bash
# After installing MSYS2, run in the MSYS2 terminal:
pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-python mingw-w64-x86_64-python-gobject
```

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/user/ERPCT.git
cd ERPCT

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install ERPCT in development mode
pip install -e .
```

## Usage

### Starting the GUI

```bash
# Using the run_gui.py script
python run_gui.py

# Or if installed via pip
erpct-gui
```

### Command Line Interface

```bash
# Basic usage
python src/main.py --target 192.168.1.100 --protocol ssh --username admin --wordlist wordlist.txt

# With more options
python src/main.py --target 192.168.1.100 --protocol http-form --port 8080 --username admin --wordlist wordlist.txt --threads 10 --delay 0.5 --output results.txt
```

### Command Line Options

- `--target`: Target hostname or IP address
- `--port`: Target port
- `--protocol`: Protocol to use (ssh, ftp, http-form, etc.)
- `--list-protocols`: List available protocols
- `--username`: Username to try
- `--password`: Password to try (for single attempts)
- `--userlist`: File containing usernames (one per line)
- `--wordlist`: Password wordlist to use
- `--threads`: Number of concurrent threads (default: 1)
- `--delay`: Delay between connection attempts in seconds (default: 0)
- `--timeout`: Connection timeout in seconds (default: 10)
- `--username-first`: Try all passwords for each username (default)
- `--password-first`: Try all usernames for each password
- `--output`: Output file for results
- `--json`: Output results in JSON format
- `--verbose`: Verbose output
- `--debug`: Debug output

## GUI Components

### Main Dashboard
The main application window provides access to all features through a dashboard interface, including:
- Configuration tools
- Attack tools
- Utilities

### Configuration Manager
The Configuration Manager allows editing various configuration files:
- Default Settings
- UI Settings
- Protocols
- Distributed attack settings
- Evasion technique settings

### Protocol Editor
The Protocol Editor provides a specialized interface for managing protocol configurations:
- Add, edit, or remove protocol definitions
- Configure protocol-specific parameters
- Organize protocols by category

## Project Structure
```
ERPCT/
├── src/
│   ├── core/           # Core cracking engine
│   ├── gui/            # GTK interface components
│   ├── protocols/      # Protocol-specific modules
│   ├── utils/          # Utility functions
│   ├── evasion/        # Evasion techniques
│   └── main.py         # CLI entry point
├── config/             # Configuration files
├── data/               # Data files
├── resources/          # UI resources
├── run_gui.py          # GUI entry point
└── requirements.txt    # Dependencies
```

## Security Considerations

- **Legal Usage**: Only use ERPCT against systems you own or have explicit permission to test
- **Network Impacts**: Password attacks can generate significant traffic and potentially trigger security alerts
- **Service Disruption**: Aggressive attacks may cause denial of service; use rate limiting features

## License

ERPCT is released under the MIT License. See the LICENSE file for details.

## Disclaimer

This tool is developed for educational purposes and legitimate security testing only. Unauthorized access to computer systems and networks is illegal and unethical. The developers assume no liability and are not responsible for any misuse or damage caused by this program.