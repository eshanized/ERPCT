# Password Mutation Rules in ERPCT

ERPCT uses a powerful rule-based system for password mutations, enabling flexible and effective password generation strategies for security testing.

## Rule System Overview

The rule-based mutation system allows you to:

1. Transform existing password lists into new variations
2. Generate pattern-based mutations based on common user behaviors
3. Create targeted mutations for specific environments or organizations
4. Optimize attack efficiency by prioritizing likely password variations

## Rule Syntax

ERPCT rules use a syntax inspired by Hashcat and John the Ripper, but with extensions for advanced functionality.

### Basic Rule Commands

| Command | Description | Example | Input → Output |
|---------|-------------|---------|---------------|
| `:` | Do nothing | `:` | password → password |
| `l` | Convert to lowercase | `l` | Password → password |
| `u` | Convert to uppercase | `u` | password → PASSWORD |
| `c` | Capitalize | `c` | password → Password |
| `C` | Lowercase first char, uppercase rest | `C` | Password → pASSWORD |
| `t` | Toggle case of all characters | `t` | pAsSwOrD → PaSsWoRd |
| `r` | Reverse | `r` | password → drowssap |
| `d` | Duplicate | `d` | password → passwordpassword |
| `p[N]` | Duplicate N times | `p2` | pass → passpasspass |
| `f` | Reflect (append reversed) | `f` | pass → passssap |
| `{` | Rotate left | `{` | password → asswordp |
| `}` | Rotate right | `}` | password → dpasswor |

### Character Substitutions

| Command | Description | Example | Input → Output |
|---------|-------------|---------|---------------|
| `s[a][b]` | Replace all a with b | `sao` | password → possword |
| `@[x]` | Purge all instances of x | `@s` | password → paword |
| `z[a][b]` | Replace first instance of a with b | `zae` | password → pessword |
| `Z[a][b]` | Replace last instance of a with b | `Zsi` | password → pasword |

### Prefixes and Suffixes

| Command | Description | Example | Input → Output |
|---------|-------------|---------|---------------|
| `^[x]` | Prepend character x | `^1` | password → 1password |
| `$[x]` | Append character x | `$1` | password → password1 |
| `^[text]` | Prepend text | `^admin` | pass → adminpass |
| `$[text]` | Append text | `$123` | pass → pass123 |

### Length Control

| Command | Description | Example | Input → Output |
|---------|-------------|---------|---------------|
| `<[N]` | Truncate to N characters | `<5` | password → passw |
| `>[N]` | Skip first N characters | `>2` | password → ssword |
| `'[N]` | Truncate all after position N | `'4` | password → pass |
| `([N]` | Delete character at position N | `(4` | password → passord |
| `)[N]` | Make position N the only one to keep | `)4` | password → w |

### Advanced Operations

| Command | Description | Example | Input → Output |
|---------|-------------|---------|---------------|
| `i[N][x]` | Insert x at position N | `i3!` | password → pas!sword |
| `o[N][x]` | Overwrite character at position N with x | `o3$` | password → pas$word |
| `D[N]` | Delete N characters from the right | `D3` | password → passw |
| `x[N][M]` | Extract substring from position N, length M | `x03` | password → pas |
| `L[N]` | Bitwise shift left by N | `L2` | password → sswordpa |

## Rule Combinations

Rules can be combined on a single line to create complex transformations:

```
# Capitalize and add year suffix
c$2023      # password → Password2023

# Replace characters and append number
sa@se3$123  # password → p@$$word123  

# Full transformation example
c sa@ se$ r $2023  # password → Dr0w$$@P2023
```

## Conditional Rules

ERPCT extends the basic rule syntax with conditional rules:

```
# Apply rule only if length > 5
?[>5] c     # password → Password, but: test → test

# Apply rule only if contains a digit
?[*d] r     # test123 → 321tset, but: test → test

# Apply rule only if first character is alphabetic
?[^a] u     # password → PASSWORD, but: 1pass → 1pass
```

## Rule Sets

ERPCT includes several built-in rule sets:

| Rule Set | Description | Location |
|----------|-------------|----------|
| `basic.rule` | Simple character substitutions and affixes | resources/rules/basic.rule |
| `leetspeak.rule` | Common leetspeak transformations | resources/rules/leetspeak.rule |
| `year_dates.rule` | Adds year and date patterns | resources/rules/year_dates.rule |
| `corporate.rule` | Common corporate password policies | resources/rules/corporate.rule |
| `complex.rule` | Advanced mutations for complex passwords | resources/rules/complex.rule |

## Creating Custom Rule Files

Custom rule files are simple text files with one rule per line:

```
# filename: my_custom.rule

# Simple transformations
c
u
l

# Add common suffixes
$1
$123
$!

# Common character substitutions
sa@
se3
si!
so0

# Combinations
c$2023
sa@$!
```

Comments start with `#` and are ignored when processing.

## Using Rules in ERPCT

### Command Line Interface

```bash
# Apply rules to a wordlist
erpct-wordlist transform --input base.txt --rules my_custom.rule --output transformed.txt

# Use rules directly in an attack
erpct --target 192.168.1.100 --protocol ssh --username admin --wordlist base.txt --rules basic.rule
```

### Graphical Interface

1. In the Password Options section, select a base wordlist
2. Enable the "Use Rules" option
3. Select a rule file from the dropdown or click "Create/Edit" to customize
4. Optionally, use the Rule Tester to preview transformations
5. Configure other attack parameters and start the attack

## Rule Optimization

### Testing Rules

ERPCT includes a rule testing utility:

```bash
# Test rules against sample inputs
erpct-wordlist test-rules --rules my_custom.rule --input sample_words.txt

# Test with verbose output showing each transformation
erpct-wordlist test-rules --rules my_custom.rule --input sample_words.txt --verbose
```

### Analyzing Rule Effectiveness

```bash
# Analyze rule effectiveness based on past successes
erpct-wordlist analyze-rules --rules my_custom.rule --success-passwords found_passwords.txt
```

### Optimizing Rule Order

The order of rules can significantly impact cracking efficiency:

```bash
# Optimize rule order based on likelihood of success
erpct-wordlist optimize-rules --input my_custom.rule --output optimized.rule
```

## Targeted Rule Creation

### Organization-Specific Rules

Create targeted rules for specific organizations by incorporating:

1. Company name variations
2. Establishment year
3. Common internal terminology
4. Known password policies

Example:
```
# ACME Corporation rules
c$acme
c$ACME
c$Acme123
c$Acme2023
sa@c$Acme!
```

### Language-Specific Rules

Different languages have different patterns for password creation:

```bash
# Load language-specific rules
erpct --target example.com --protocol http-form --username admin --wordlist french_words.txt --rules french.rule
```

## Performance Considerations

1. **Rule Complexity**: Complex rules generate more candidates, requiring more processing time
2. **Rule Order**: Order rules from most to least likely for best performance
3. **Memory Usage**: Very large rule sets combined with large wordlists can consume significant memory
4. **Testing**: Test rule effectiveness on sample datasets before running full attacks

## Advanced Rule Techniques

### Dictionary Word Mangling

```
# Combine two words from wordlist
+[wordlist.txt]
```

### Character Class Aware Rules

```
# Only apply to passwords with special characters
?[*s] r

# Only apply to passwords without digits
?[-d] $123
```

### Pattern Matching

```
# Apply rule only to passwords matching pattern
?[=p*a*s*s*] u
```

## Integration with Attack Strategies

Different protocols and targets may benefit from different rule sets:

| Target Type | Recommended Rule Set |
|-------------|---------------------|
| Web Applications | basic.rule, leetspeak.rule |
| Corporate Networks | corporate.rule, year_dates.rule |
| Personal Accounts | leetspeak.rule, basic.rule |
| Legacy Systems | simple.rule |

## Security Considerations

Remember to use ERPCT's rule-based password attacks only against systems you own or have explicit permission to test.
