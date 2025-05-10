#!/usr/bin/env python3
"""
Python Project Generator

This script creates a new Python project with all necessary files and initializes a Git repository.
"""

import os
import sys
import argparse
import subprocess
import venv
from pathlib import Path

DEFAULT_PROJECTS_DIR = os.path.join(os.getenv("DEFAULT_PROJECTS_DIR", os.path.expanduser("~/Coding")), "projects")


def open_in_sublime(project_path):
    """Open the project in Sublime Text."""
    try:
        project_name = os.path.basename(project_path)
        sublime_project = os.path.join(project_path, ".sublime-workspace", f"{project_name}.sublime-project")
        subprocess.run(["subl", "--project", sublime_project], check=True)
        print("Opened project in Sublime Text")
    except subprocess.CalledProcessError as e:
        print(f"Failed to open Sublime Text: {e}")
    except FileNotFoundError:
        print("Sublime Text is not installed or not in PATH")


def create_project_structure(project_name, project_path):
    """
    Create the project directory structure and files.

    Args:
        project_name (str): Name of the project
        project_path (str): Path where project should be created
    """
    # Create project directory
    full_path = os.path.join(project_path, project_name)
    os.makedirs(full_path, exist_ok=True)

    # Change to project directory
    os.chdir(full_path)

    # Convert project name to snake case for package name (if it has hyphens)
    package_name = project_name.replace('-', '_')

    # Create main package directory
    os.makedirs(package_name, exist_ok=True)

    # Create __init__.py in the package directory
    with open(f"{package_name}/__init__.py", "w") as f:
        f.write(f'"""Main package for {project_name}."""\n\n__version__ = "0.1.0"\n')

    # Create main.py in the package directory
    with open(f"{package_name}/main.py", "w") as f:
        f.write(f'''"""Main module for {project_name}."""

def main():
    """Run the main function."""
    print("Hello from {project_name}!")

if __name__ == "__main__":
    main()
''')

    # Create README.md
    with open("README.md", "w") as f:
        f.write(f"# {project_name}\n\nA Python project.\n\n## Installation\n\n```bash\n# Create and activate virtual environment\npython -m venv .venv\nsource .venv/bin/activate  # On Windows: .venv\\Scripts\\activate\n\n# Install the package in development mode\npip install -e .\n```\n\n## Usage\n\n```python\nimport {package_name}\n```\n")

    # Create setup.py
    with open("setup.py", "w") as f:
        f.write(f'''"""Setup script for {project_name}."""

from setuptools import setup, find_packages

setup(
    name="{project_name}",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Add your dependencies here
    ],
    entry_points={{
        "console_scripts": [
            "{project_name}={package_name}.main:main",
        ],
    }},
)
''')

    # Create .gitignore
    with open(".gitignore", "w") as f:
        f.write('''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
dist/
build/
*.egg-info/

# Virtual environments
.venv/
venv/
ENV/

# IDE specific files
.idea/
.vscode/
*.sublime-*

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
coverage.xml
*.cover
''')

    # Create directory for sublime project files
    os.makedirs(".sublime-workspace", exist_ok=True)

    # Create .sublime-project file with LSP settings
    sublime_project_path = os.path.join(".sublime-workspace", f"{project_name}.sublime-project")
    with open(sublime_project_path, "w") as f:
        project_path = os.path.abspath(".")
        f.write(f'''{{
    "folders": [
        {{
            "path": "{project_path}"
        }}
    ],
    "settings": {{
        "LSP": {{
            "LSP-pyright": {{
                "settings": {{
                    "python": {{
                        "pythonPath": "{project_path}/.venv/bin/python",
                        "venvPath": "{project_path}",
                        "venv": ".venv"
                    }}
                }}
            }}
        }}
    }}
}}''')

    # Create requirements.txt (initial empty)
    with open("requirements.txt", "w") as f:
        f.write('''# Project dependencies
# Add your dependencies here, one per line
# Example:
# requests>=2.25.1
''')


def create_virtual_env():
    """Create a virtual environment in the project directory."""
    print("Creating virtual environment...")
    venv.create(".venv", with_pip=True)
    print("Virtual environment created at .venv/")


def init_git_repo():
    """Initialize a Git repository in the project directory."""
    try:
        print("Initializing Git repository...")
        subprocess.run(["git", "init"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Git repository initialized.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to initialize Git repository: {e}")
    except FileNotFoundError:
        print("Git is not installed or not in PATH. Please install Git to initialize the repository.")


def main():
    """Run the main function."""
    parser = argparse.ArgumentParser(description="Generate a new Python project.")
    parser.add_argument("--name", "-n", type=str, help="Name of the project")
    parser.add_argument("--path", "-p", type=str, help=f"Path to create project {DEFAULT_PROJECTS_DIR}")
    parser.add_argument("--open", "-o", action="store_true", help="Open in Sublime Text after creation")
    parser.add_argument("--no-open", action="store_true", help="Skip opening in Sublime Text")

    args = parser.parse_args()

    # Get project name from command line or interactively
    project_name = args.name
    if not project_name:
        project_name = input("Enter project name: ").strip()

    # Validate project name
    if not project_name:
        print("Project name cannot be empty.")
        sys.exit(1)

    # Determine project path
    project_path = os.path.expanduser(args.path) if args.path else DEFAULT_PROJECTS_DIR
    os.makedirs(project_path, exist_ok=True)

    full_project_path = os.path.join(project_path, project_name)
    if os.path.exists(full_project_path):
        response = input(f"Directory '{full_project_path}' already exists. Overwrite? (y/N): ").lower()
        if response != 'y':
            print("Project creation cancelled.")
            sys.exit(1)

    # Create project files
    print(f"Creating project '{project_name}' in {project_path}...")
    create_project_structure(project_name, project_path)

    # Create virtual environment
    create_virtual_env()

    # Initialize Git repository
    init_git_repo()

    # Convert project name to package name
    package_name = project_name.replace('-', '_')

    # Print success message
    current_dir = os.path.abspath(os.curdir)
    print(f"\nProject '{project_name}' created successfully at {current_dir}")
    print(f"\nPackage name: {package_name}")
    print("\nNext steps:")
    print(f"1. cd {full_project_path}")
    print("2. Activate the virtual environment:")
    print("   - On Linux/macOS: source .venv/bin/activate")
    print("   - On Windows: .venv\\Scripts\\activate")
    print("3. Install the package in development mode: pip install -e .")

    # Handle Sublime Text opening
    if not args.no_open:
        if args.open:
            open_in_sublime(full_project_path)
        else:
            response = input("\nOpen project in Sublime Text? [y/N]: ").lower()
            if response == 'y':
                open_in_sublime(full_project_path)


if __name__ == "__main__":
    main()
