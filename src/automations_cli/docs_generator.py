#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from helper.configs import setup_logging
except ImportError:
    from .helper.configs import setup_logging

logger = setup_logging(log_file="docs_generator.log")

# --- Constants ---
DEFAULT_LICENSE = "MIT"
README_TEMPLATE = """# {project_name}

A {description} project.

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
requires-python = ">=3.8"
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
    "pytest>=7.0",
    "ruff>=0.3.0",
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


# --- Helper Functions ---
def create_readme(
    output_dir: Path, project_name: str, license: str, description: str
) -> None:
    """Create a README.md file."""
    readme_path = output_dir / "README.md"
    content = README_TEMPLATE.format(
        project_name=project_name, description=description, license=license
    )
    try:
        readme_path.write_text(content, encoding="utf-8")
        logger.info(f"Created README.md at {readme_path}")
    except Exception as e:
        logger.error(f"Failed to create README.md: {e}")
        raise


def create_pyproject(
    output_dir: Path,
    project_name: str,
    package_name: str,
    license: str,
    author: str,
    email: str,
    description: str,
) -> None:
    """Create a pyproject.toml file."""
    pyproject_path = output_dir / "pyproject.toml"
    content = PYPROJECT_TEMPLATE.format(
        project_name=project_name,
        package_name=package_name,
        license=license,
        author=author,
        email=email,
        description=description,
    )
    try:
        pyproject_path.write_text(content, encoding="utf-8")
        logger.info(f"Created pyproject.toml at {pyproject_path}")
    except Exception as e:
        logger.error(f"Failed to create pyproject.toml: {e}")
        raise


def create_gitignore(output_dir: Path) -> None:
    """Create a .gitignore file."""
    gitignore_path = output_dir / ".gitignore"
    try:
        gitignore_path.write_text(GITIGNORE_TEMPLATE, encoding="utf-8")
        logger.info(f"Created .gitignore at {gitignore_path}")
    except Exception as e:
        logger.error(f"Failed to create .gitignore: {e}")
        raise


def create_license_file(output_dir: Path, license_type: str, author: str) -> None:
    """Create a LICENSE file based on the specified license type."""
    license_path = output_dir / "LICENSE"
    year = datetime.now().year
    content = LICENSE_TEMPLATES.get(license_type, LICENSE_TEMPLATES["MIT"]).format(
        year=year, author=author
    )
    try:
        license_path.write_text(content, encoding="utf-8")
        logger.info(f"Created LICENSE ({license_type}) at {license_path}")
    except Exception as e:
        logger.error(f"Failed to create LICENSE: {e}")
        raise


def validate_output_dir(output_dir: Path) -> None:
    """Validate and create output directory if it doesn't exist."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        test_file = output_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        logger.debug(f"Output directory validated: {output_dir}")
    except PermissionError as e:
        logger.error(f"Permission denied for output directory {output_dir}: {e}")
        print(f"❌ Permission denied: {output_dir}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to validate output directory {output_dir}: {e}")
        print(f"❌ Error with output directory: {e}", file=sys.stderr)
        sys.exit(1)


def validate_args(args: argparse.Namespace) -> None:
    """Validate command-line arguments."""
    doc_flags = [args.readme, args.license, args.pyproject, args.gitignore, args.all]
    if not any(doc_flags):
        logger.error("No document flags provided")
        print(
            "❌ Error: At least one of --all, --readme, --license, --pyproject, or --gitignore must be specified.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check for invalid use of --author or --email
    uses_author_or_email = (
        args.author != "Your Name" or args.email != "your.email@example.com"
    )
    needs_author_or_email = args.all or args.readme or args.license or args.pyproject
    if uses_author_or_email and not needs_author_or_email:
        logger.error("Author or email provided without relevant document flags")
        print(
            "❌ Error: --author or --email can only be used with --all, --readme, --license, or --pyproject.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check for invalid use of --package-name
    if args.package_name and not (args.all or args.pyproject):
        logger.error("Package name provided without pyproject flag")
        print(
            "❌ Error: --package-name can only be used with --all or --pyproject.",
            file=sys.stderr,
        )
        sys.exit(1)


def main():
    """Main function to generate documentation files."""
    parser = argparse.ArgumentParser(
        description="Generate project documentation files (README.md, LICENSE, pyproject.toml, .gitignore).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all --dir ./my_project
  %(prog)s --readme --license --project-name my_app --author "Jane Doe"
  %(prog)s --pyproject --gitignore --dir ./docs
""",
    )
    parser.add_argument(
        "--dir",
        default=".",
        help="Output directory for documentation files (default: current directory)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all documentation files (README.md, LICENSE, pyproject.toml, .gitignore)",
    )
    parser.add_argument(
        "--readme",
        action="store_true",
        help="Generate README.md",
    )
    parser.add_argument(
        "--license",
        action="store_true",
        help="Generate LICENSE",
    )
    parser.add_argument(
        "--pyproject",
        action="store_true",
        help="Generate pyproject.toml",
    )
    parser.add_argument(
        "--gitignore",
        action="store_true",
        help="Generate .gitignore",
    )
    parser.add_argument(
        "--project-name",
        default="my_project",
        help="Project name for README and pyproject.toml (default: my_project)",
    )
    parser.add_argument(
        "--package-name",
        default=None,
        help="Package name for pyproject.toml (defaults to project-name with underscores)",
    )
    parser.add_argument(
        "--description",
        default="A Python project",
        help="Project description for README and pyproject.toml (default: A Python project)",
    )
    parser.add_argument(
        "--author",
        default="Your Name",
        help="Author name for LICENSE and pyproject.toml (default: Your Name)",
    )
    parser.add_argument(
        "--email",
        default="your.email@example.com",
        help="Author email for pyproject.toml (default: your.email@example.com)",
    )
    parser.add_argument(
        "--license-type",
        choices=["MIT", "Apache-2.0", "GPL-3.0"],
        default=DEFAULT_LICENSE,
        help=f"License type (default: {DEFAULT_LICENSE})",
    )

    args = parser.parse_args()

    # Validate arguments
    validate_args(args)

    # Set up output directory
    output_dir = Path(args.dir).expanduser().resolve()
    validate_output_dir(output_dir)

    # Use project name for package name if not specified
    package_name = args.package_name or args.project_name.replace("-", "_")

    logger.info(f"Generating documentation files in {output_dir}")
    print(f"Generating documentation files in {output_dir}")

    try:
        # Generate files based on flags
        if args.all or args.readme:
            create_readme(
                output_dir, args.project_name, args.license_type, args.description
            )
        if args.all or args.pyproject:
            create_pyproject(
                output_dir,
                args.project_name,
                package_name,
                args.license_type,
                args.author,
                args.email,
                args.description,
            )
        if args.all or args.gitignore:
            create_gitignore(output_dir)
        if args.all or args.license:
            create_license_file(output_dir, args.license_type, args.author)

        print(f"✅ Successfully generated documentation files in {output_dir}")
        logger.info(f"Documentation generation completed successfully")

    except Exception as e:
        logger.error(f"Failed to generate documentation: {e}")
        print(f"❌ Error generating documentation: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
