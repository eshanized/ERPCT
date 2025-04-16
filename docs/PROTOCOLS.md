# Supported Protocols in ERPCT

ERPCT supports a wide range of protocols for security testing purposes. This document details the implementation, configuration options, and best practices for each protocol.

## Core Protocols

### SSH

```
Protocol: ssh
Default Port: 22
```

**Configuration Options:**
- `username`: Username to authenticate with
- `password_list`: Path to password wordlist
- `key_auth`: Enable/disable key-based authentication attempts
- `timeout`: Connection timeout in seconds
- `banner_delay`: Time to wait after banner before sending credentials

**Example:**
```bash
erpct --target 192.168.1.10 --protocol ssh --username root --wordlist common_passwords.txt
```

### FTP

```
Protocol: ftp
Default Port: 21
```

**Configuration Options:**
- `username`: Username to authenticate with
- `password_list`: Path to password wordlist
- `use_ssl`: Use FTPS (FTP over SSL/TLS)
- `passive_mode`: Use passive mode connection
- `timeout`: Connection timeout in seconds

**Example:**
```bash
erpct --target ftp.example.com --protocol ftp --username admin --wordlist ftp_passwords.txt --use-ssl
```

### HTTP(S)

#### HTTP Basic Authentication

```
Protocol: http-basic
Default Port: 80/443
```

**Configuration Options:**
- `username`: Username to authenticate with
- `password_list`: Path to password wordlist
- `url_path`: Specific URL path requiring authentication
- `use_ssl`: Use HTTPS instead of HTTP
- `verify_ssl`: Verify SSL certificate
- `user_agent`: Custom User-Agent header

**Example:**
```bash
erpct --target www.example.com --protocol http-basic --url-path /admin --username admin --wordlist web_passwords.txt
```

#### HTTP Form Authentication

```
Protocol: http-form
Default Port: 80/443
```

**Configuration Options:**
- `url`: Full URL of the login form
- `method`: HTTP method (GET/POST)
- `form_data`: Form data template with ^USER^ and ^PASS^ markers
- `success_match`: Text pattern indicating successful login
- `failure_match`: Text pattern indicating failed login
- `csrf_token_field`: Name of CSRF token field, if any
- `captcha_detection`: Pattern to detect CAPTCHA presence

**Example:**
```bash
erpct --target example.com --protocol http-form --url https://example.com/login --method POST --form-data "username=^USER^&password=^PASS^" --success-match "Welcome"
```

### SMTP

```
Protocol: smtp
Default Port: 25/465/587
```

**Configuration Options:**
- `username`: Username/email to authenticate with
- `password_list`: Path to password wordlist
- `use_ssl`: Use SSL/TLS from start
- `use_starttls`: Use STARTTLS after connection
- `auth_method`: Authentication method (PLAIN, LOGIN, CRAM-MD5)

**Example:**
```bash
erpct --target mail.example.com --protocol smtp --port 587 --username user@example.com --wordlist email_passwords.txt --use-starttls
```

### SMB

```
Protocol: smb
Default Port: 445
```

**Configuration Options:**
- `username`: Username to authenticate with
- `password_list`: Path to password wordlist
- `domain`: Windows domain (optional)
- `workgroup`: SMB workgroup
- `share`: Target share name
- `version`: SMB protocol version (1, 2, 3)

**Example:**
```bash
erpct --target 192.168.1.100 --protocol smb --username administrator --domain WORKGROUP --wordlist windows_passwords.txt
```

### RDP

```
Protocol: rdp
Default Port: 3389
```

**Configuration Options:**
- `username`: Username to authenticate with
- `password_list`: Path to password wordlist
- `domain`: Windows domain (optional)
- `security_level`: RDP security level
- `timeout`: Connection timeout in seconds

**Example:**
```bash
erpct --target 192.168.1.50 --protocol rdp --username admin --domain CORP --wordlist rdp_passwords.txt
```

### Telnet

```
Protocol: telnet
Default Port: 23
```

**Configuration Options:**
- `username`: Username to authenticate with
- `password_list`: Path to password wordlist
- `prompt_regex`: Regular expression to identify login/password prompts
- `success_regex`: Regular expression to identify successful login
- `timeout`: Connection and read timeout in seconds

**Example:**
```bash
erpct --target 192.168.1.1 --protocol telnet --username cisco --wordlist network_devices.txt
```

## Database Protocols

### MySQL

```
Protocol: mysql
Default Port: 3306
```

**Configuration Options:**
- `username`: Username to authenticate with
- `password_list`: Path to password wordlist
- `database`: Database name (optional)
- `timeout`: Connection timeout in seconds

**Example:**
```bash
erpct --target db.example.com --protocol mysql --username root --wordlist db_passwords.txt
```

### PostgreSQL

```
Protocol: postgres
Default Port: 5432
```

**Configuration Options:**
- `username`: Username to authenticate with
- `password_list`: Path to password wordlist
- `database`: Database name (default: postgres)
- `ssl_mode`: SSL mode (disable, allow, prefer, require)

**Example:**
```bash
erpct --target 192.168.1.20 --protocol postgres --username postgres --wordlist postgres_passwords.txt
```

### MongoDB

```
Protocol: mongodb
Default Port: 27017
```

**Configuration Options:**
- `username`: Username to authenticate with
- `password_list`: Path to password wordlist
- `database`: Authentication database (default: admin)
- `mechanism`: Authentication mechanism (SCRAM-SHA-1, SCRAM-SHA-256)

**Example:**
```bash
erpct --target mongo.example.com --protocol mongodb --username admin --wordlist mongo_passwords.txt
```

## Other Protocols

### LDAP

```
Protocol: ldap
Default Port: 389/636
```

**Configuration Options:**
- `bind_dn`: Distinguished Name for binding
- `password_list`: Path to password wordlist
- `use_ssl`: Use LDAPS (LDAP over SSL)
- `search_base`: Base DN for search operations
- `timeout`: Connection timeout in seconds

**Example:**
```bash
erpct --target ldap.example.com --protocol ldap --bind-dn "cn=admin,dc=example,dc=com" --wordlist ldap_passwords.txt
```

### VNC

```
Protocol: vnc
Default Port: 5900
```

**Configuration Options:**
- `password_list`: Path to password wordlist
- `timeout`: Connection timeout in seconds

**Example:**
```bash
erpct --target 192.168.1.30 --protocol vnc --wordlist vnc_passwords.txt
```

## Extending Protocol Support

ERPCT is designed to be easily extensible with new protocol modules. See [EXTENDING.md](EXTENDING.md) for details on how to implement a new protocol.

## Security and Ethical Considerations

When performing protocol-based password cracking:

1. **Only test systems you own or have explicit permission to test**
2. **Be aware of account lockout policies**
3. **Understand that aggressive cracking may cause denial of service**
4. **Follow compliance requirements for your organization**

## Protocol-Specific Evasion Techniques

ERPCT implements protocol-specific evasion techniques to help avoid detection. See [EVASION.md](EVASION.md) for detailed information on protocol-specific evasion configuration.
