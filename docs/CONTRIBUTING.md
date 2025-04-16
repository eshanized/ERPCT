# Contributing to ERPCT

We appreciate your interest in contributing to ERPCT! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to uphold our Code of Conduct, which ensures a welcoming and inclusive environment for all contributors.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/ERPCT.git
   cd ERPCT
   ```
3. **Set up the development environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```
4. **Create a new branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

1. **Make your changes**
2. **Run the tests** to ensure your changes don't break existing functionality:
   ```bash
   pytest
   ```
3. **Format your code**:
   ```bash
   black src/ tests/
   isort src/ tests/
   ```
4. **Run linting**:
   ```bash
   flake8 src/ tests/
   ```
5. **Commit your changes** with a descriptive commit message:
   ```bash
   git commit -m "Add feature X that implements Y"
   ```
6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Create a pull request** to the main repository

## Pull Request Guidelines

- Provide a clear description of the changes and their purpose
- Include any relevant issue numbers in the PR description
- Ensure all tests pass
- Update relevant documentation
- Add tests for new features or bug fixes

## Code Style

We follow the PEP 8 style guide for Python code with a few adjustments:
- Maximum line length of 100 characters
- Use type hints whenever possible
- Use docstrings for all public functions, classes, and methods
- Organize imports using `isort`
- Format code using `black`

## Adding New Features

### Protocol Support

If you're adding a new protocol:
1. Create a new file in `src/protocols/`
2. Implement the required interfaces from `src/protocols/base.py`
3. Add tests in `tests/protocols/`
4. Document the protocol in `docs/PROTOCOLS.md`
5. Register the protocol in `config/protocols.json`

### UI Components

When adding new UI components:
1. Follow the existing pattern in `src/gui/`
2. Ensure the UI is responsive and accessible
3. Add appropriate translations if applicable

## Reporting Bugs

When reporting bugs, please include:
- A clear description of the issue
- Steps to reproduce
- Expected vs. actual behavior
- Version information (Python, OS, ERPCT version)
- Screenshots if applicable

## Feature Requests

Feature requests are welcome! Please provide:
- A clear description of the feature
- The use case or problem it addresses
- Any implementation ideas you have

## Documentation

When updating documentation:
- Maintain the same tone and style as existing documentation
- Use markdown formatting consistently
- Update all relevant files (README.md, docs/, etc.)

## License

By contributing to ERPCT, you agree that your contributions will be licensed under the project's MIT license.

## Questions?

If you have any questions, feel free to open an issue or contact the maintainers directly.

Thank you for contributing to ERPCT!
