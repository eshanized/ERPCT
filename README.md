# ERPCT - Enhanced Rapid Password Cracking Tool

![ERPCT Logo](resources/images/erpct_logo.png)

ERPCT is an advanced password cracking tool with a GTK-based graphical user interface, designed to be a more powerful, customizable, and feature-rich alternative to THC-Hydra. It supports multiple protocols and implements sophisticated attack strategies for security testing purposes.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GTK 3/4](https://img.shields.io/badge/GTK-3/4-green.svg)](https://www.gtk.org/)

## 🔥 Features

- **Multi-Protocol Support**
  - SSH, FTP, HTTP(S), SMTP, Telnet, RDP, SMB, and more
  - Extensible architecture for custom protocol implementations

- **Advanced Cracking Techniques**
  - Dictionary attacks with comprehensive wordlists
  - Rule-based password mutations
  - Hybrid attacks combining multiple strategies
  - Smart attack scheduling based on protocol characteristics

- **Powerful GTK-based User Interface**
  - Intuitive target and attack configuration
  - Real-time attack status and progress monitoring
  - Interactive results explorer
  - Wordlist and rule management

- **Performance Optimizations**
  - Multi-threaded architecture for concurrent cracking
  - Asynchronous operations for network-bound protocols
  - Efficient memory management for handling large wordlists
  - Optional distributed cracking across multiple machines

- **Advanced Evasion Capabilities**
  - Customizable timing patterns to avoid detection
  - IP rotation and proxy support
  - Protocol-specific evasion techniques
  - Failed attempt limiting and smart retry logic

- **Comprehensive Logging and Analysis**
  - Detailed attack logs for post-engagement analysis
  - Success/failure statistics
  - Performance metrics and optimization suggestions

## 📋 Requirements

- Python 3.8 or higher
- GTK 3/4 with PyGObject
- Additional protocol-specific dependencies as per requirements.txt

## 🔧 Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/eshanized/ERPCT.git
cd ERPCT

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install ERPCT in development mode
pip install -e .
```

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
Windows users should consider using [MSYS2](https://www.msys2.org/) to install GTK and its dependencies:
```bash
# After installing MSYS2, run in the MSYS2 terminal:
pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-python mingw-w64-x86_64-python-gobject
```

## 🚀 Usage

### Graphical Interface

```bash
# Launch ERPCT GUI
erpct
```

### Command Line Interface

```bash
# Basic usage
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist resources/wordlists/common.txt

# Advanced options
erpct --target targets.txt --protocol http-form --port 8080 --form-data "username=^USER^&password=^PASS^" --success-match "Welcome" --username-list users.txt --wordlist passlist.txt --threads 10 --delay 2
```

## 📖 Documentation

### Getting Started

1. **Target Configuration**
   - Single Target: Enter the IP address or hostname and port
   - Multiple Targets: Import a list of targets from a file

2. **Protocol Selection**
   - Choose the protocol to attack from the dropdown menu
   - Configure protocol-specific parameters

3. **Credentials**
   - Specify usernames (single or list)
   - Choose a wordlist for passwords or generate one

4. **Attack Options**
   - Set thread count and connection timeout
   - Configure proxy settings if needed
   - Adjust evasion parameters

5. **Execution**
   - Start the attack and monitor progress
   - View and save results

### Advanced Usage

#### Wordlist Management

ERPCT includes a wordlist manager for creating, importing, and manipulating password lists:

- Import from standard formats (txt, csv)
- Apply transformation rules to generate variants
- Analyze and optimize wordlists for specific targets
- Combine multiple wordlists with deduplication

#### Evasion Techniques

Configure attack patterns to minimize detection:

- Randomized delays between attempts
- Dynamic timing based on server response
- Connection throttling
- IP rotation through proxies

#### Custom Protocol Extensions

Extend ERPCT with custom protocol modules:

1. Create a new protocol file in `src/protocols/`
2. Implement the required interfaces from `src/protocols/base.py`
3. Register the protocol in `config/protocols.json`

## 🔐 Security Considerations

- **Legal Usage**: Only use ERPCT against systems you own or have explicit permission to test
- **Network Impacts**: Password attacks can generate significant traffic and potentially trigger security alerts
- **Service Disruption**: Aggressive attacks may cause denial of service; use rate limiting features
- **Sensitive Data**: Handle discovered credentials securely and responsibly

## 🛠️ Development

### Project Structure

```
ERPCT/
├── src/
│   ├── core/           # Core cracking engine
│   ├── gui/            # GTK interface components
│   ├── protocols/      # Protocol-specific modules
│   ├── utils/          # Utility functions
│   ├── wordlists/      # Wordlist generation and handling
│   ├── evasion/        # Evasion techniques
│   └── main.py         # Application entry point
├── resources/
│   ├── wordlists/      # Default wordlists
│   ├── rules/          # Password mangling rules
│   └── images/         # UI assets
├── docs/               # Documentation
├── tests/              # Unit and integration tests
└── config/             # Configuration files
```

### Contributing

We welcome contributions to ERPCT! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for details on how to submit pull requests, report issues, or request features.

### Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_protocols.py
```

## 📜 License

ERPCT is released under the MIT License. See [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is developed for educational purposes and legitimate security testing only. Unauthorized access to computer systems and networks is illegal and unethical. The developers assume no liability and are not responsible for any misuse or damage caused by this program.

## 📬 Contact

For questions, suggestions, or collaboration opportunities, please open an issue on the GitHub repository or contact the maintainers at:

- Email: your.email@example.com
- Project Issues: [GitHub Issues](https://github.com/eshanized/ERPCT/issues)