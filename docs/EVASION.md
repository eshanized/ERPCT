# Evasion Techniques in ERPCT

ERPCT includes sophisticated evasion capabilities to help avoid detection during security testing. This document details the available evasion techniques and their implementation.

## Overview

Evasion techniques are essential for:

1. Avoiding triggering intrusion detection systems (IDS)
2. Preventing account lockouts
3. Reducing the risk of being blacklisted
4. Making password testing more stealthy
5. Simulating more realistic attack patterns

## Basic Evasion Options

### Time-Based Evasion

Control the timing of authentication attempts to appear less aggressive:

```bash
# Add a fixed delay between attempts
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --delay 2

# Use random delays between attempts
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --random-delay 1-5

# Use exponential backoff after failures
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --backoff-delay
```

### Connection Limiting

Control how many connections are attempted:

```bash
# Limit maximum simultaneous connections
erpct --target 192.168.1.100 --protocol http-form --username admin --wordlist passwords.txt --max-connections 3

# Limit total attempts per time window
erpct --target 192.168.1.100 --protocol smtp --username admin --wordlist passwords.txt --rate-limit 10/minute
```

### IP Rotation

Distribute attempts across multiple source IPs:

```bash
# Use a list of proxy servers
erpct --target 192.168.1.100 --protocol http-form --username admin --wordlist passwords.txt --proxy-list proxies.txt

# Rotate between specific IPs on a multi-homed system
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --source-ips 192.168.1.50,192.168.1.51
```

## Advanced Evasion Techniques

### Protocol-Specific Evasion

#### HTTP Evasion

```bash
# Rotate User-Agent strings
erpct --target example.com --protocol http-form --username admin --wordlist passwords.txt --user-agent-rotation

# Add random URL parameters
erpct --target example.com --protocol http-form --username admin --wordlist passwords.txt --random-url-params

# Use HTTP header randomization
erpct --target example.com --protocol http-form --username admin --wordlist passwords.txt --header-randomization
```

#### SSH Evasion

```bash
# Use multiple key exchange algorithms
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --kex-rotation

# Modulate banner grabbing behavior
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --banner-delay 1-3
```

#### SMTP Evasion

```bash
# Change greeting behavior
erpct --target mail.example.com --protocol smtp --username admin --wordlist passwords.txt --greeting-rotation
```

### Session Pattern Evasion

Control the pattern of authentication attempts:

```bash
# Use non-sequential password testing
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --non-sequential

# Distribute attempts across multiple targets
erpct --target targets.txt --protocol ssh --username admin --wordlist passwords.txt --target-rotation
```

## Evasion Configuration File

You can define complex evasion profiles in a configuration file:

```bash
# Use an evasion profile
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --evasion-profile stealth.json
```

Example `stealth.json` configuration:

```json
{
  "timing": {
    "min_delay": 2,
    "max_delay": 8,
    "jitter": 0.5,
    "backoff": {
      "enabled": true,
      "factor": 2,
      "max_delay": 30
    }
  },
  "connection": {
    "max_simultaneous": 2,
    "limit_per_host": 5,
    "rate_limit": "10/minute"
  },
  "ip_rotation": {
    "enabled": true,
    "proxy_list": "proxies.txt",
    "rotation_strategy": "round-robin"
  },
  "protocol_specific": {
    "http": {
      "user_agent_rotation": true,
      "header_randomization": true,
      "cookie_handling": "session_based"
    },
    "ssh": {
      "kex_rotation": true,
      "client_version_rotation": true
    }
  },
  "pattern": {
    "non_sequential": true,
    "password_grouping": "random"
  }
}
```

## GUI Evasion Configuration

In the ERPCT graphical interface, evasion settings are configured in the "Evasion" tab:

1. **Timing Controls**: Configure delays between attempts
2. **Connection Settings**: Limit simultaneous connections
3. **IP Rotation**: Configure proxy usage
4. **Protocol-Specific Options**: Set protocol-specific evasion techniques
5. **Pattern Settings**: Control the pattern of authentication attempts

## Failure Handling and Smart Retries

ERPCT includes smart retry logic to handle transient failures:

```bash
# Configure maximum retries for failed connections
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --max-retries 3

# Enable smart retry behavior
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --smart-retry
```

Smart retry features include:

- Distinguishing between connection failures and authentication failures
- Exponential backoff for repeated connection failures
- Automatic service detection to adapt to server behavior
- Handling of rate-limiting responses

## Detecting and Adapting to Defense Mechanisms

ERPCT can detect and adapt to various defense mechanisms:

### Account Lockout Detection

```bash
# Enable account lockout detection
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --detect-lockout

# Test with canary accounts
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --canary-accounts canaries.txt
```

### Blacklist Detection

```bash
# Monitor for blacklisting
erpct --target 192.168.1.100 --protocol http-form --username admin --wordlist passwords.txt --blacklist-detection
```

## Protocol-Specific Evasion Details

### HTTP/HTTPS Evasion Techniques

| Technique | Description | Configuration |
|-----------|-------------|---------------|
| User-Agent Rotation | Cycle through different browser user-agents | `--user-agent-rotation` |
| Referrer Spoofing | Use realistic referrer headers | `--referrer-spoofing` |
| Cookie Handling | Maintain proper cookie state | `--cookie-handling session` |
| Accept Headers | Use realistic accept headers | `--accept-header-rotation` |
| Request Timing | Mimic human timing between requests | `--human-timing` |
| URL Parameter Randomization | Add random URL parameters | `--random-url-params` |

### SSH Evasion Techniques

| Technique | Description | Configuration |
|-----------|-------------|---------------|
| Client Version Rotation | Change SSH client version | `--client-version-rotation` |
| Key Exchange Algorithm Rotation | Vary key exchange algorithms | `--kex-rotation` |
| Cipher Rotation | Use different cipher suites | `--cipher-rotation` |
| Banner Delay | Vary timing after banner receipt | `--banner-delay 1-3` |
| Connection Sequence | Vary the connection sequence | `--connection-pattern random` |

### FTP Evasion Techniques

| Technique | Description | Configuration |
|-----------|-------------|---------------|
| Passive/Active Mode Switching | Switch between passive and active mode | `--ftp-mode-switching` |
| Command Pacing | Control timing between FTP commands | `--command-pacing 1-3` |
| Welcome Delay | Vary delay after welcome message | `--welcome-delay 1-2` |

## Custom Evasion Modules

ERPCT supports custom evasion modules:

```bash
# Use a custom evasion module
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist passwords.txt --custom-evasion my_evasion.py
```

Example of a custom evasion module:

```python
# my_evasion.py
from src.evasion.base import EvasionBase
import time
import random

class CustomEvasion(EvasionBase):
    """Custom evasion implementation"""
    
    def __init__(self, config=None):
        super().__init__(config or {})
        self.custom_param = self.config.get("custom_param", "default")
    
    def pre_auth(self):
        """Called before authentication attempt"""
        # Custom pre-authentication logic
        time.sleep(random.uniform(1, 3))
    
    def post_auth(self, success):
        """Called after authentication attempt"""
        # Custom post-authentication logic
        if not success:
            time.sleep(random.uniform(2, 5))
```

See [EXTENDING.md](EXTENDING.md) for more details on implementing custom evasion modules.

## Evasion Best Practices

1. **Start conservative**: Begin with minimal evasion and increase as needed
2. **Test in safe environments**: Verify evasion techniques in controlled environments first
3. **Monitor for lockouts**: Pay attention to account lockout policies
4. **Use realistic patterns**: Configure evasion to mimic realistic user behavior
5. **Protocol awareness**: Use protocol-specific evasion techniques when available
6. **Adapt to target**: Different targets require different evasion strategies

## Legal and Ethical Considerations

When using evasion techniques:

1. **Only test systems you own or have explicit permission to test**
2. **Understand that evasion techniques may violate terms of service**
3. **Document all testing activities**
4. **Consider the potential impact on production systems**

## Troubleshooting Evasion Issues

Common issues and solutions:

- **Excessive slowness**: Adjust timing parameters to balance stealth and performance
- **Proxy failures**: Ensure proxy list contains valid, functioning proxies
- **Detection despite evasion**: Some advanced security systems may still detect the testing
- **Resource exhaustion**: IP rotation and connection management can consume resources

## References

- [NIST SP 800-115: Technical Guide to Information Security Testing](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-115.pdf)
- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Mitre ATT&CK Framework - Defense Evasion](https://attack.mitre.org/tactics/TA0005/)
