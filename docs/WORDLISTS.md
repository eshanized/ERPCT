# Wordlist Management in ERPCT

ERPCT provides powerful tools for creating, managing, and optimizing password wordlists for more effective security testing.

## Built-in Wordlists

ERPCT comes with several built-in wordlists:

| Wordlist | Description | Size | Location |
|----------|-------------|------|----------|
| common.txt | Common passwords across various services | 10,000 | resources/wordlists/common.txt |
| system.txt | System and device default credentials | 5,000 | resources/wordlists/system.txt |
| web.txt | Web application specific passwords | 15,000 | resources/wordlists/web.txt |
| database.txt | Database service passwords | 8,000 | resources/wordlists/database.txt |
| leaked.txt | Known leaked passwords (sample) | 20,000 | resources/wordlists/leaked.txt |

## Wordlist Tools

ERPCT includes dedicated tools for wordlist management:

```bash
# Basic wordlist tool usage
erpct-wordlist [OPERATION] [OPTIONS]
```

### Wordlist Operations

#### Generating Wordlists

```bash
# Generate a wordlist based on patterns
erpct-wordlist generate --patterns "Company{2023,2024}" --output company_passwords.txt

# Generate permutations of base words
erpct-wordlist generate --base-words "admin,user,system" --mutations "Aa@" --output permutations.txt
```

#### Combining Wordlists

```bash
# Combine multiple wordlists with deduplication
erpct-wordlist combine --input list1.txt,list2.txt,list3.txt --output combined.txt --deduplicate
```

#### Transforming Wordlists

```bash
# Apply transformation rules to existing wordlist
erpct-wordlist transform --input base_list.txt --rules rules.txt --output transformed.txt
```

#### Filtering Wordlists

```bash
# Filter wordlist by length
erpct-wordlist filter --input large_list.txt --min-length 8 --max-length 16 --output filtered.txt

# Filter by character types
erpct-wordlist filter --input large_list.txt --require-uppercase --require-digits --output complex_passwords.txt
```

#### Analyzing Wordlists

```bash
# Analyze password composition and patterns
erpct-wordlist analyze --input wordlist.txt --output analysis.json
```

## Password Mutation Rules

ERPCT uses a powerful rule-based system for password mutations. Rules are defined in text files with specific syntax.

### Rule Syntax

Each rule consists of a series of transformation operations:

```
# Basic substitutions
s@a@       # Substitute 'a' with '@'
s$s$       # Substitute 's' with '$'

# Case transformations
c           # Capitalize first letter
u           # Convert to uppercase
l           # Convert to lowercase

# Prefixes and suffixes
^123        # Add '123' prefix
$123        # Add '123' suffix

# Truncation
<8          # Truncate to 8 characters
>5          # Remove first 5 characters

# Reversing
r           # Reverse the string
```

### Rule Examples

```
# Example rules.txt file
c$2023      # Capitalize and add '2023' suffix
sa@$123     # Replace 'a' with '@' and add '123' suffix
r^admin     # Reverse and add 'admin' prefix
```

### Using Rules

```bash
# Apply rules to a wordlist
erpct-wordlist transform --input base.txt --rules rules.txt --output mutated.txt

# Use rules directly in ERPCT
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist base.txt --rules rules.txt
```

## Wordlist Management in GUI

ERPCT's graphical interface includes a Wordlist Manager for interactive wordlist operations:

1. **Import/Export**: Import external wordlists or export current lists
2. **Editor**: Edit wordlists directly within the application
3. **Analysis**: Visualize password patterns and statistics
4. **Rule Builder**: Create and test mutation rules with live preview
5. **Optimization**: Optimize wordlists for specific target types

## Optimizing Wordlists

Password cracking efficiency can be improved with targeted wordlist optimization:

### Target-Specific Optimization

```bash
# Optimize for web applications
erpct-wordlist optimize --input large_list.txt --target-type web --output web_optimized.txt

# Optimize for network devices
erpct-wordlist optimize --input large_list.txt --target-type network --output network_optimized.txt
```

### Statistical Optimization

```bash
# Sort by probability based on character analysis
erpct-wordlist optimize --input large_list.txt --sort-by probability --output probability_sorted.txt

# Create a subset of most likely passwords
erpct-wordlist optimize --input large_list.txt --select-top 10000 --output most_likely.txt
```

## External Wordlist Integration

ERPCT can integrate with external wordlist resources:

### Importing Common Wordlists

```bash
# Import from SecLists
erpct-wordlist import --source seclists --category passwords --output imported.txt

# Import from other sources
erpct-wordlist import --source url --url "https://example.com/wordlists/passwords.txt" --output downloaded.txt
```

### Wordlist Format Conversion

```bash
# Convert between formats
erpct-wordlist convert --input hashcat_format.txt --output erpct_format.txt
```

## Performance Considerations

When working with large wordlists:

1. **Memory Usage**: Very large wordlists may require substantial RAM
2. **Processing Time**: Rule application to large lists can be time-consuming
3. **Storage Requirements**: Consider compression for large collections

### Chunking Large Wordlists

```bash
# Split a large wordlist into manageable chunks
erpct-wordlist split --input huge_list.txt --chunk-size 1000000 --output-prefix chunk_
```

## Security Best Practices

When managing wordlists:

1. **Secure Storage**: Store wordlists securely with appropriate file permissions
2. **Sensitive Content**: Be aware that wordlists may contain sensitive information
3. **Legal Compliance**: Ensure compliance with applicable laws and regulations
4. **Ethical Use**: Only use for authorized security testing

## Integration with Attack Strategies

Effective wordlist selection based on target type:

| Target Type | Recommended Wordlist | Recommended Rules |
|-------------|----------------------|-------------------|
| Web Applications | web.txt | webapp_rules.txt |
| Network Devices | network.txt | simple_rules.txt |
| Databases | database.txt | complex_rules.txt |
| Windows Systems | windows.txt | windows_rules.txt |
| Linux Systems | linux.txt | unix_rules.txt |
