#!/usr/bin/env python3
"""
Python Project Generator

This script creates a new Python project with all necessary files,
initializes a Git repository, and supports both uv and standard pip/venv workflows.
"""

import os
import sys
import argparse
import subprocess
import venv
from pathlib import Path

from helper import setup_logging

# Assuming 'helper.py' with a confirm function exists in the same directory or a reachable path.
# from helper import confirm, setup_logging


def confirm(prompt):
    """Get user confirmation."""
    while True:
        reply = input(f"{prompt} [y/N]: ").lower().strip()
        if reply in ["y", "yes"]:
            return True
        if reply in ["n", "no", ""]:
            return False


DEFAULT_PROJECTS_DIR = os.path.join(
    os.getenv("DEFAULT_PROJECTS_DIR", os.path.expanduser("~/Coding")), "projects"
)

logger = setup_logging(log_file="project_generator.log")


def check_uv_installed():
    """Check if uv is installed on the system."""
    try:
        subprocess.run(
            ["uv", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def open_in_sublime(project_path):
    """Open the project in Sublime Text."""
    try:
        project_name = os.path.basename(project_path)
        sublime_project = os.path.join(
            project_path, ".sublime-workspace", f"{project_name}.sublime-project"
        )
        subprocess.run(["subl", "--project", sublime_project], check=True)
        logger.info("Opened project in Sublime Text")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open Sublime Text: {e}")
    except FileNotFoundError:
        logger.error("Sublime Text is not installed or not in PATH")


def create_minimal_pyproject_toml(
    project_name,
    package_name,
    use_src_layout=False,
    is_app=False,
    is_bin=False,
    has_readme=False,
):
    """Create a minimal pyproject.toml file."""
    readme_line = 'readme = "README.md"\n' if has_readme else ""

    if is_app:
        pyproject_content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "Add your description here"
{readme_line}requires-python = ">=3.8"
dependencies = []
'''
    else:
        build_backend = "hatchling.build"
        packages_config = ""
        if use_src_layout:
            packages_config = (
                f'\n[tool.hatch.build.targets.wheel]\npackages = ["src/{package_name}"]'
            )

        entry_point = ""
        if is_bin:
            main_path = f"{package_name}.main:main"
            if use_src_layout:
                main_path = f"src.{package_name}.main:main"

            entry_point = (
                f'''\n[project.scripts]\n{project_name} = "{package_name}.main:main"'''
            )

        pyproject_content = f'''[build-system]
requires = ["hatchling"]
build-backend = "{build_backend}"

[project]
name = "{project_name}"
version = "0.1.0"
description = "Add your description here"
{readme_line}requires-python = ">=3.8"
dependencies = []{entry_point}{packages_config}
'''

    with open("pyproject.toml", "w") as f:
        f.write(pyproject_content)


def create_license_file(license_type):
    """Create a LICENSE file (MIT example)."""
    if license_type.upper() == "MIT":
        license_content = """MIT License

Copyright (c) 2025 Your Name

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
"""
        with open("LICENSE", "w") as f:
            f.write(license_content)
        logger.info("Created MIT LICENSE file.")


def create_project_files(project_name, package_name, args):
    """Create the project directory structure and files based on arguments."""
    # Determine the main source directory
    base_dir = Path("src") / package_name if args.src else Path(package_name)

    # Create main package directory
    base_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py
    (base_dir / "__init__.py").write_text(
        f'"""Main package for {project_name}."""\n\n__version__ = "0.1.0"\n'
    )

    # Create main module for library or binary
    if not args.app:
        main_content = f'''"""Main module for {project_name}."""

def main():
    """Run the main function."""
    print("Hello from {project_name}!")

if __name__ == "__main__":
    main()
'''
        (base_dir / "main.py").write_text(main_content)

    # Create app.py for app structure
    if args.app:
        Path("app.py").write_text(f'''"""Main application for {project_name}."""

def main():
    """Run the application."""
    print("Hello from {project_name} app!")

if __name__ == "__main__":
    main()
''')


def create_readme(project_name, package_name, args):
    """Create README.md file."""
    usage_section = ""
    if args.app:
        usage_section = "## Usage\n\n```bash\npython app.py\n```"
    elif args.bin:
        usage_section = (
            f"## Usage\n\n```bash\n# After installation\n{project_name}\n```"
        )
    else:
        usage_section = f"## Usage\n\n```python\nimport {package_name}\n\n{package_name}.main.main()\n```"

    installation_section = "## Installation\n\n```bash\npip install -e .\n```"
    readme_content = f"# {project_name}\n\nAdd your description here\n\n{installation_section}\n\n{usage_section}\n"
    Path("README.md").write_text(readme_content)
    logger.info("Created README.md.")


def create_gitignore():
    """Create a comprehensive .gitignore file."""
    Path(".gitignore").write_text("""# Python
__pycache__/
.rufff_cache
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/
env/

# IDEs
.vscode/
*.sublime-*
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log
""")
    logger.info("Created .gitignore.")


def create_sublime_project(project_name):
    """Create Sublime Text project files with settings."""
    workspace_dir = Path(".sublime-workspace")
    workspace_dir.mkdir(exist_ok=True)

    project_file = workspace_dir / f"{project_name}.sublime-project"
    project_path_abs = Path.cwd().as_posix()  # Use POSIX paths for consistency

    project_content = f'''{{
    "folders": [
        {{
            "path": "{project_path_abs}"
        }}
    ],
    "settings": {{
        "LSP": {{
            "LSP-pyright": {{
                "settings": {{
                    "python": {{
                        "pythonPath": "{project_path_abs}/.venv/bin/python",
                        "venvPath": "{project_path_abs}",
                        "venv": ".venv"
                    }}
                }}
            }}
        }}
    }},
    "build_systems": [
        {{
            "name": "{project_name}",
            "target": "terminus_exec",
            "cancel": "terminus_cancel_build",
            "title": "{project_name}",
            "auto_close": false,
            "focus": true,
            "shell_cmd": "{project_path_abs}/.venv/bin/python -u \\"$file\\"",
            "file_regex": "^[ ]*File \\"(...*?)\\", line ([0-9]*)",
            "working_dir": "${{file_path}}",
            "selector": "source.python",
            "file_patterns": ["*.py"]
        }}
    ]
}}'''
    project_file.write_text(project_content)
    logger.info("Created Sublime Text project files.")


def setup_dependencies(use_uv, create_venv):
    """Set up dependencies and virtual environment using uv or pip."""
    if not create_venv:
        logger.info("Skipping virtual environment creation.")
        return

    if use_uv:
        logger.info("Setting up project with uv...")
        try:
            subprocess.run(["uv", "sync"], check=True)
            logger.info("Dependencies and venv handled by uv.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set up dependencies with uv: {e}")
            sys.exit("uv sync failed. Please check the project configuration.")
    else:
        logger.info("Setting up project with pip and venv...")
        create_virtual_env_pip()


def create_virtual_env_pip():
    """Create a virtual environment and install package using pip."""
    logger.info("Creating virtual environment with venv...")
    # Use EnvBuilder with symlinks=False to be more robust
    builder = venv.EnvBuilder(with_pip=True, symlinks=False)
    builder.create(".venv")
    logger.info("Virtual environment created at .venv/")

    try:
        pip_path = ".venv/Scripts/pip" if os.name == "nt" else ".venv/bin/pip"
        subprocess.run([pip_path, "install", "-e", "."], check=True)
        logger.info("Package installed in development mode using pip.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install package with pip: {e}")


def init_git_repo(skip_git):
    """Initialize a Git repository."""
    if skip_git:
        logger.info("Skipping Git repository initialization.")
        return
    try:
        logger.info("Initializing Git repository...")
        subprocess.run(
            ["git", "init"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        logger.info("Git repository initialized.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Failed to initialize Git repository: {e}")


def main():
    """Main function to run the project generator."""
    parser = argparse.ArgumentParser(
        description="Generate a new Python project with uv support and flexible templates.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Project Templates:
  --app                            Simple script-like app (app.py)
  --src --bin                      CLI tool with a src layout
  --src                            Standard library/SDK with a src layout
  --no-venv                        Quick prototype without a virtual env

Examples:
  %(prog)s my-app --app
  %(prog)s my-cli --src --bin --license MIT
  %(prog)s my-lib --src --readme
  %(prog)s quick-test --app --no-venv --no-git
""",
    )
    # Basic options
    parser.add_argument("name", nargs="?", help="Name of the project")
    parser.add_argument(
        "--path",
        "-p",
        type=str,
        help=f"Path to create project (default: {DEFAULT_PROJECTS_DIR})",
    )
    # Project structure
    parser.add_argument(
        "--src", action="store_true", help="Use src/ layout for packaging"
    )
    parser.add_argument(
        "--app",
        action="store_true",
        help="Create a simple application structure (app.py)",
    )
    parser.add_argument(
        "--bin",
        action="store_true",
        help="Configure project as a CLI tool with an entry point",
    )
    # File generation
    parser.add_argument(
        "--readme", action="store_true", help="Generate a README.md file"
    )
    parser.add_argument("--license", type=str, help="Add a license file (e.g., MIT)")
    # Environment
    parser.add_argument(
        "--no-venv", action="store_true", help="Skip virtual environment creation"
    )
    parser.add_argument(
        "--no-uv",
        action="store_true",
        help="Force use of pip/venv even if uv is installed",
    )
    # Git
    parser.add_argument(
        "--no-git", action="store_true", help="Skip Git repository initialization"
    )
    # IDE
    parser.add_argument(
        "--open", "-o", action="store_true", help="Open in Sublime Text after creation"
    )
    parser.add_argument(
        "--no-open", action="store_true", help="Skip opening in Sublime Text"
    )
    args = parser.parse_args()

    project_name = args.name or input("Enter project name: ").strip()
    if not project_name:
        logger.error("Project name cannot be empty.")
        sys.exit(1)

    project_path = Path(args.path or DEFAULT_PROJECTS_DIR).expanduser()
    project_path.mkdir(exist_ok=True)

    full_project_path = project_path / project_name
    if full_project_path.exists():
        if not confirm(f"Directory '{full_project_path}' already exists. Overwrite?"):
            logger.info("Project creation cancelled.")
            sys.exit(0)

    # Change to the project's parent directory, then create and move into it.
    os.chdir(project_path)
    full_project_path.mkdir(exist_ok=True)
    os.chdir(full_project_path)

    logger.info(f"Creating project '{project_name}' in {full_project_path}...")

    package_name = project_name.replace("-", "_")
    create_venv = not args.no_venv
    use_uv = not args.no_uv and check_uv_installed()
    will_create_readme = args.readme or args.bin or (args.src and not args.app)

    # Create all project files
    create_project_files(project_name, package_name, args)
    create_minimal_pyproject_toml(
        project_name, package_name, args.src, args.app, args.bin, will_create_readme
    )
    create_gitignore()
    create_sublime_project(project_name)  # Sublime integration
    if will_create_readme:
        create_readme(project_name, package_name, args)
    if args.license:
        create_license_file(args.license)

    # Set up environment and dependencies
    if create_venv:
        if use_uv:
            logger.info("uv detected - using it for dependency management.")
        else:
            logger.info("uv not found or disabled - using pip/venv.")
    setup_dependencies(use_uv, create_venv)

    # Initialize Git repository
    init_git_repo(args.no_git)

    logger.info(
        f"\n✅ Project '{project_name}' created successfully at {full_project_path}"
    )

    # Print next steps
    logger.info("\nNext steps:")
    logger.info(f"1. cd {full_project_path}")
    if create_venv:
        logger.info(
            "2. source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate"
        )
        if args.app:
            logger.info("3. python app.py")
        elif args.bin:
            logger.info(f"3. {project_name}")
        else:
            logger.info("3. Start coding!")
    else:
        if args.app:
            logger.info("2. python app.py")
        else:
            logger.info("2. Start coding!")

    # Handle Sublime Text opening
    if not args.no_open:
        if args.open or confirm("\nOpen project in Sublime Text?"):
            open_in_sublime(str(full_project_path))


if __name__ == "__main__":
    main()
