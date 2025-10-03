DEFAULT_LICENSE = "MIT"

LICENSE_TEMPLATES = {
    "MIT": """MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""",
    "Apache-2.0": """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

1. Definitions.
...

[Full Apache 2.0 License text would go here. Truncated for brevity.
You can find the full text at: http://www.apache.org/licenses/LICENSE-2.0]
""",
    "GPL-3.0": """GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (c) {year} {author}

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
""",
}

README_TEMPLATE = """# {project_name}

{description}

## Installation

```bash
pip install -e .
```

## Usage

```bash
{project_name} --help
```

## Contributing

Contributions are welcome! Please open an issue or pull request.

## License

This project is licensed under the {license} License - see the [LICENSE](LICENSE) file for details.
"""

PYPROJECT_TEMPLATE = """[project]
name = "{project_name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.9"
license = {{ text = "{license}" }}
authors = [
    {{ name = "{author}", email = "{email}" }},
]
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{package_name}"]

[project.optional-dependencies]
dev = [
    "pytest>=8.4",
    "pytest-mock>=3.14",
    "pytest-asyncio>=0.24",
    "ruff>=0.6",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.ruff]
line-length = 88
target-version = "py38"

[project.scripts]
run-project = "{package_name}.main:main"
"""

GITIGNORE_TEMPLATE = """# Python
*.pyc
__pycache__/
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-wheel-metadata/
build/
dist/
*.egg-info/

# Logs
logs/
*.log

# IDEs and editors
.vscode/
.idea/
*.sublime-*

# OS generated files
.DS_Store
Thumbs.db

# Testing
.coverage
coverage.xml
*.cover

# Cache
.ruff_cache/
.pytest_cache/
"""
