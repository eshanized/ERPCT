# Extending ERPCT

ERPCT is designed with extensibility in mind, allowing developers to add new protocols, attack methods, and features. This document provides guidelines for extending ERPCT's functionality.

## Architecture Overview

ERPCT follows a modular architecture, with clear separation between core components:

```
ERPCT/
├── src/
│   ├── core/           # Core attack engine
│   ├── protocols/      # Protocol implementations
│   ├── gui/            # User interface components
│   ├── wordlists/      # Wordlist handling
│   ├── evasion/        # Evasion techniques
│   └── utils/          # Utility functions
```

## Adding New Protocols

One of the most common extensions is adding support for new protocols.

### Protocol Interface

All protocol modules must implement the `ProtocolBase` abstract class from `src/protocols/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any

class ProtocolBase(ABC):
    """Base class for all protocol implementations"""
    
    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        """Initialize the protocol with configuration"""
        pass
    
    @abstractmethod
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test a single username/password combination
        
        Returns:
            Tuple containing (success_bool, optional_message)
        """
        pass
    
    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """Return the configuration schema for this protocol
        
        Used by the UI to generate protocol-specific configuration fields
        """
        pass
        
    @property
    @abstractmethod
    def default_port(self) -> int:
        """Return the default port for this protocol"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this protocol"""
        pass
    
    @property
    def supports_username_enumeration(self) -> bool:
        """Whether this protocol supports username enumeration"""
        return False
    
    def cleanup(self) -> None:
        """Clean up any resources. Called when attack is complete."""
        pass
```

### Step-by-Step Protocol Implementation

1. **Create a new file** in `src/protocols/` named after your protocol (e.g., `src/protocols/custom_protocol.py`)

2. **Implement the required class**:

```python
from typing import Dict, Optional, Tuple, Any
from src.protocols.base import ProtocolBase
from src.utils.logging import get_logger

class CustomProtocol(ProtocolBase):
    """Custom protocol implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.host = config.get("host")
        self.port = config.get("port", self.default_port)
        self.timeout = config.get("timeout", 10)
        # Protocol-specific configuration
        self.custom_option = config.get("custom_option", "default_value")
        
    def test_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Test a single username/password combination"""
        self.logger.debug(f"Testing {username}:{password} on {self.host}:{self.port}")
        
        try:
            # Implement actual authentication logic here
            # This is protocol-specific code
            connection = self._connect_to_service()
            success = self._authenticate(connection, username, password)
            
            if success:
                return True, f"Successfully authenticated as {username}"
            else:
                return False, None
                
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            return False, f"Error: {str(e)}"
            
    def _connect_to_service(self):
        # Protocol-specific connection code
        pass
        
    def _authenticate(self, connection, username, password):
        # Protocol-specific authentication code
        pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return configuration schema for UI generation"""
        return {
            "type": "object",
            "required": ["host"],
            "properties": {
                "port": {
                    "type": "integer",
                    "title": "Port",
                    "default": self.default_port
                },
                "timeout": {
                    "type": "integer",
                    "title": "Timeout (seconds)",
                    "default": 10
                },
                "custom_option": {
                    "type": "string",
                    "title": "Custom Option",
                    "default": "default_value"
                }
            }
        }
    
    @property
    def default_port(self) -> int:
        return 12345  # Default port for your protocol
    
    @property
    def name(self) -> str:
        return "custom_protocol"
    
    def cleanup(self) -> None:
        """Clean up resources"""
        # Close connections, etc.
        pass
```

3. **Register your protocol** in `config/protocols.json`:

```json
{
  "protocols": [
    // Existing protocols
    {
      "name": "custom_protocol",
      "display_name": "Custom Protocol",
      "module": "src.protocols.custom_protocol",
      "class": "CustomProtocol",
      "description": "Description of your custom protocol",
      "category": "other"
    }
  ]
}
```

4. **Add protocol-specific tests** in `tests/protocols/test_custom_protocol.py`

### Protocol Best Practices

- **Error Handling**: Implement robust error handling for network issues
- **Timeouts**: Always use timeouts for network operations
- **Logging**: Use the ERPCT logging framework for consistent logs
- **Resource Management**: Properly close connections in `cleanup()`
- **Thread Safety**: Ensure your protocol implementation is thread-safe
- **User Feedback**: Provide meaningful error messages

## Adding Custom Wordlist Processors

You can extend the wordlist processing capabilities:

1. **Create a new processor** in `src/wordlists/processors/`:

```python
from src.wordlists.processors.base import WordlistProcessorBase

class CustomProcessor(WordlistProcessorBase):
    """Custom wordlist processor"""
    
    def __init__(self, config=None):
        super().__init__(config or {})
        self.custom_option = self.config.get("custom_option", "default")
    
    def process(self, wordlist):
        """Process the wordlist"""
        result = []
        for word in wordlist:
            # Custom processing logic
            result.append(self._transform_word(word))
        return result
    
    def _transform_word(self, word):
        # Custom transformation logic
        return word
```

2. **Register your processor** in `config/wordlist_processors.json`

## Adding GUI Components

To extend the GUI with new components:

1. **Create UI components** in `src/gui/components/`:

```python
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class CustomWidget(Gtk.Box):
    """Custom GTK widget"""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Create and add child widgets
        self.label = Gtk.Label(label="Custom Widget")
        self.button = Gtk.Button(label="Click Me")
        self.button.connect("clicked", self.on_button_clicked)
        
        self.pack_start(self.label, False, False, 0)
        self.pack_start(self.button, False, False, 0)
        
    def on_button_clicked(self, widget):
        """Handle button click"""
        print("Button clicked")
```

2. **Integrate** your widget into the main UI in the appropriate place

## Implementing Evasion Techniques

To add new evasion techniques:

1. **Create a new evasion module** in `src/evasion/`:

```python
from src.evasion.base import EvasionBase
import time
import random

class CustomEvasion(EvasionBase):
    """Custom evasion technique"""
    
    def __init__(self, config=None):
        super().__init__(config or {})
        self.min_delay = self.config.get("min_delay", 1)
        self.max_delay = self.config.get("max_delay", 5)
    
    def pre_auth(self):
        """Called before authentication attempt"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
    
    def post_auth(self, success):
        """Called after authentication attempt"""
        if success:
            # Do something different if successful
            pass
```

2. **Register your evasion technique** in `config/evasion.json`

## Creating Custom Attack Methods

To implement a new attack method:

1. **Create a new attack class** in `src/core/attacks/`:

```python
from src.core.attacks.base import AttackBase
from typing import Dict, List, Any

class CustomAttack(AttackBase):
    """Custom attack implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.custom_option = config.get("custom_option", "default")
    
    def prepare(self):
        """Prepare for the attack"""
        # Setup code here
        
    def execute(self):
        """Execute the attack"""
        # Implementation of your custom attack method
        
    def stop(self):
        """Stop the attack"""
        # Cleanup and stop the attack
```

2. **Register your attack** in `config/attacks.json`

## Plugin System

ERPCT also supports a plugin system for more complex extensions:

1. **Create a plugin** in `plugins/myplugin/`:

```
plugins/myplugin/
├── __init__.py
├── plugin.json
├── myplugin.py
└── resources/
```

2. **Define plugin metadata** in `plugin.json`:

```json
{
  "name": "myplugin",
  "version": "1.0.0",
  "description": "My custom ERPCT plugin",
  "author": "Your Name",
  "entry_point": "myplugin.MyPlugin",
  "requires": ["core>=1.0.0"]
}
```

3. **Implement plugin class** in `myplugin.py`:

```python
from src.plugins.base import PluginBase

class MyPlugin(PluginBase):
    """Custom plugin implementation"""
    
    def __init__(self):
        super().__init__()
        
    def initialize(self):
        """Initialize the plugin"""
        self.logger.info("Initializing MyPlugin")
        
    def get_protocols(self):
        """Return custom protocols"""
        return [
            {
                "name": "myplugin_protocol",
                "class": "MyPluginProtocol"
            }
        ]
        
    def get_ui_components(self):
        """Return custom UI components"""
        return [
            {
                "name": "myplugin_tab",
                "class": "MyPluginTab",
                "container": "main_notebook"
            }
        ]
```

## API Integration

To integrate with the ERPCT API:

1. **Create API handlers** in `src/api/handlers/`:

```python
from src.api.base import APIHandlerBase

class CustomAPIHandler(APIHandlerBase):
    """Custom API endpoint handler"""
    
    def __init__(self):
        super().__init__()
        
    def get(self, request):
        """Handle GET request"""
        return {"status": "success", "data": "Custom data"}
        
    def post(self, request):
        """Handle POST request"""
        data = request.get_json()
        # Process data
        return {"status": "success", "message": "Data processed"}
```

2. **Register your API endpoint** in `config/api.json`

## Documentation

When extending ERPCT:

1. **Document your code** with detailed docstrings
2. **Update relevant documentation** files in the `docs/` directory
3. **Add examples** showing how to use your extension
4. **Include tests** to verify functionality

## Contribution Guidelines

Before submitting your extension:

1. Follow the code style guidelines in [CONTRIBUTING.md](CONTRIBUTING.md)
2. Ensure all tests pass: `pytest`
3. Verify your extension works with both the CLI and GUI interfaces
4. Submit a pull request with a clear description of your extension
