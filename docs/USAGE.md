# ERPCT Usage Guide

This guide provides detailed instructions for using ERPCT for security testing purposes.

## Installation

Before using ERPCT, ensure it's properly installed:

```bash
# Install from PyPI
pip install erpct

# Or install from source
git clone https://github.com/eshanized/ERPCT.git
cd ERPCT
pip install -e .
```

## Graphical User Interface

ERPCT provides a feature-rich GTK-based interface for intuitive operation.

### Starting the GUI

```bash
# Launch ERPCT GUI
erpct
```

### GUI Components

The ERPCT interface consists of the following main areas:

#### 1. Target Configuration Panel

- **Target Input**: Enter hostname, IP address, or load targets from a file
- **Protocol Selector**: Choose the protocol to attack
- **Protocol Options**: Configure protocol-specific settings

#### 2. Authentication Panel

- **Username Input**: Enter a single username or load from a file
- **Password Options**: Select wordlist, rules, or generate passwords

#### 3. Attack Configuration

- **Thread Control**: Set the number of concurrent threads
- **Timing Options**: Configure delays and timing patterns
- **Proxy Settings**: Set up proxy rotation for evasion

#### 4. Results Panel

- **Live Status**: View current attack progress
- **Success Table**: See discovered credentials
- **Log Viewer**: Monitor detailed operation logs

### Workflow Example

1. Enter the target IP or hostname: `192.168.1.100`
2. Select the protocol: `SSH`
3. Configure protocol options: Port `22`
4. Enter the username: `admin` or select a username list
5. Select a password wordlist: `resources/wordlists/common.txt`
6. Configure threads: `10`
7. Set timing options: Random delay between `1-3` seconds
8. Click `Start Attack`
9. Monitor progress and results in the Results Panel

## Command Line Interface

ERPCT provides a powerful command-line interface for scripting and automation.

### Basic Usage

```bash
erpct --target TARGET --protocol PROTOCOL [OPTIONS]
```

### Common Options

```
--target TARGET         Target hostname, IP address, or file containing targets
--protocol PROTOCOL     Protocol to use (ssh, ftp, http-form, etc.)
--port PORT             Port number to connect to
--username USERNAME     Single username to try
--userlist FILE         File containing usernames
--wordlist FILE         Password wordlist to use
--rules FILE            Password mangling rules
--threads NUM           Number of concurrent threads
--timeout SECONDS       Connection timeout
--delay SECONDS         Delay between connection attempts
--output FILE           Output file for results
--verbose               Enable verbose output
--debug                 Enable debug logging
```

### Protocol-Specific Options

#### SSH Example

```bash
erpct --target 192.168.1.10 --protocol ssh --port 22 --username root --wordlist passwords.txt --threads 5
```

#### HTTP Form Example

```bash
erpct --target example.com --protocol http-form \
  --url "https://example.com/login.php" \
  --form-data "username=^USER^&password=^PASS^" \
  --success-match "Welcome" \
  --username admin \
  --wordlist web_passwords.txt \
  --threads 3
```

#### Multiple Targets Example

```bash
# targets.txt contains one target per line
erpct --target targets.txt --protocol ftp --username anonymous --wordlist passwords.txt
```

## Advanced Features

### Using Password Rules

```bash
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist base_passwords.txt --rules mutations.rule
```

### Distributed Cracking

ERPCT supports distributed password cracking across multiple machines:

```bash
# On the controller machine
erpct --distributed-controller --port 5000 --target 192.168.1.100 --protocol ssh --username admin --wordlist large_wordlist.txt

# On worker machines
erpct --distributed-worker --controller 192.168.1.5:5000
```

See [DISTRIBUTED.md](DISTRIBUTED.md) for detailed distributed cracking setup.

### Session Management

ERPCT allows saving and resuming attack sessions:

```bash
# Save session
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist huge_list.txt --save-session ssh_attack

# Resume session
erpct --resume-session ssh_attack
```

### Evasion Techniques

Configure evasion to avoid detection:

```bash
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt \
  --random-delay 1-5 \
  --max-retries 3 \
  --proxy-list proxies.txt
```

See [EVASION.md](EVASION.md) for detailed evasion configuration options.

## Configuration Files

ERPCT supports configuration files to save commonly used settings:

```bash
# Create a config file
erpct --save-config my_config.ini

# Use a config file
erpct --config my_config.ini
```

Example configuration file:

```ini
[General]
threads = 10
timeout = 5
output = results.txt

[Evasion]
random_delay = 1-3
max_attempts_per_auth = 3
```

## Wordlist Management

ERPCT includes wordlist management tools:

```bash
# Generate wordlist variations
erpct-wordlist --input base_list.txt --rules rules.txt --output expanded_list.txt

# Analyze and optimize a wordlist
erpct-wordlist --analyze wordlist.txt --optimize
```

See [WORDLISTS.md](WORDLISTS.md) for detailed wordlist management.

## Security Considerations

When using ERPCT, consider the following security best practices:

1. Always obtain proper authorization before testing
2. Start with small wordlists and low thread counts
3. Be aware of account lockout policies
4. Use evasion techniques responsibly
5. Handle discovered credentials securely

## Troubleshooting

### Common Issues

- **Connection failures**: Check network connectivity and firewall settings
- **High memory usage**: Reduce thread count or split wordlists
- **Slow performance**: Adjust timeout settings and consider network conditions
- **False positives**: Refine success/failure detection patterns

### Debugging

Enable debug logging for troubleshooting:

```bash
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --debug
```

### Getting Help

Display help information:

```bash
erpct --help
erpct --help-protocols
```

## Integrations

ERPCT can integrate with other security tools:

- Export results in formats compatible with reporting tools
- Import targets from vulnerability scanners
- Use API for integration with security orchestration platforms

See the [API documentation](api/README.md) for integration details.
