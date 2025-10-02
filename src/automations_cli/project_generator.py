#!/usr/bin/env python3
import os
import sys
import venv
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

from helper import setup_logging, confirm
from helper.templates import (
    LICENSE_TEMPLATES,
    README_TEMPLATE,
    PYPROJECT_TEMPLATE,
    GITIGNORE_TEMPLATE,
)


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


def prompt_if_missing(value, prompt, default=None, choices=None):
    if value:
        return value
    prompt_str = prompt
    if choices:
        prompt_str += f" ({'/'.join(choices)})"
    if default:
        prompt_str += f" [{default}]"
    prompt_str += ": "
    while True:
        answer = input(prompt_str).strip()
        if not answer and default is not None:
            return default
        if choices and answer and answer not in choices:
            print(f"Please choose from: {', '.join(choices)}")
            continue
        if answer:
            return answer
        if default is not None:
            return default


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


def validate_args(args):
    """Validate command-line arguments for the new flag set."""
    if args.type not in ("app", "cli", "lib"):
        logger.error("Invalid project type specified.")
        print("❌ Error: --type must be one of: app, cli, lib.", file=sys.stderr)
        sys.exit(1)
    # No other complex validation needed with the new flag set


def create_project_files(project_name, package_name, is_app, is_cli, use_src_layout):
    """Create the project directory structure and files based on project type."""
    # Determine the main source directory
    base_dir = Path("src") / package_name if use_src_layout else Path(package_name)

    # Create main package directory
    base_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py
    (base_dir / "__init__.py").write_text(
        f'"""Main package for {project_name}."""\n\n__version__ = "0.1.0"\n'
    )

    # Create main module for library or binary
    if not is_app:
        main_content = f'''"""Main module for {project_name}."""

def main():
    """Run the main function."""
    print("Hello from {project_name}!")

if __name__ == "__main__":
    main()
'''
        (base_dir / "main.py").write_text(main_content)

    # Create app.py for app structure
    if is_app:
        Path("app.py").write_text(f'''"""Main application for {project_name}."""

def main():
    """Run the application."""
    print("Hello from {project_name} app!")

if __name__ == "__main__":
    main()
''')


def create_pyproject_toml(
    project_name,
    package_name,
    use_src_layout,
    is_app,
    is_cli,
    has_readme,
    description,
    license_type,
    author="Onehand-Coding",
    email="onehand.coding433@gmail.com"
):
    """Create a pyproject.toml file using the template."""
    readme_line = 'readme = "README.md"\n' if has_readme else ""

    if is_app:
        pyproject_content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "{description}"
{readme_line}requires-python = ">=3.9"
dependencies = []
'''
    else:
        pyproject_content = PYPROJECT_TEMPLATE.format(
            project_name=project_name,
            package_name=package_name,
            description=description,
            license=license_type,
            author=author,
            email=email,
        )
        if is_cli:
            main_path = f"{package_name}.main:main"
            if use_src_layout:
                main_path = f"src.{package_name}.main:main"
            pyproject_content = pyproject_content.replace(
                f'[project.scripts]\nrun-project = "{package_name}.main:main"',
                f'[project.scripts]\n{project_name} = "{main_path}"',
            )
        if use_src_layout and "[tool.hatch.build.targets.wheel]" in pyproject_content:
            pyproject_content = pyproject_content.replace(
                f'packages = ["src/{package_name}"]',
                f'packages = ["src/{package_name}"]',
            )
        elif use_src_layout:
            pyproject_content += (
                f'\n[tool.hatch.build.targets.wheel]\npackages = ["src/{package_name}"]'
            )

    with open("pyproject.toml", "w") as f:
        f.write(pyproject_content)
    logger.info("Created pyproject.toml.")


def create_license_file(license_type, author="Onehand-Coding"):
    """Create a LICENSE file using the template."""
    year = datetime.now().year
    content = LICENSE_TEMPLATES.get(
        license_type.upper(), LICENSE_TEMPLATES["MIT"]
    ).format(year=year, author=author)
    with open("LICENSE", "w") as f:
        f.write(content)
    logger.info(f"Created {license_type} LICENSE file.")


def create_readme(project_name, package_name, description, license_type):
    """Create README.md file using the template."""
    usage_section = ""
    # Use the new type flags to determine usage section
    if Path("app.py").exists():
        usage_section = "## Usage\n\n```bash\npython app.py\n```"
    elif Path("src").exists() or Path(package_name).exists():
        usage_section = f"## Usage\n\n```python\nimport {package_name}\n\n{package_name}.main.main()\n```"
    else:
        usage_section = (
            f"## Usage\n\n```bash\n# After installation\n{project_name}\n```"
        )

    content = README_TEMPLATE.format(
        project_name=project_name,
        description=description,
        license=license_type,
    ).replace("## Usage\n\n```bash\n{project_name} --help\n```", usage_section)

    Path("README.md").write_text(content)
    logger.info("Created README.md.")


def create_gitignore():
    """Create a .gitignore file using the template."""
    Path(".gitignore").write_text(GITIGNORE_TEMPLATE)
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


def setup_dependencies(create_venv):
    """Set up dependencies and virtual environment using uv or pip."""
    if not create_venv:
        logger.info("Skipping virtual environment creation.")
        return

    use_uv = check_uv_installed()
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
        description="Generate a new Python project with flexible templates.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Project Types:
  --type app        Simple script-like app (app.py)
  --type cli        CLI tool with entry point
  --type lib        Standard library/SDK (default)

Examples:
  %(prog)s my-app --type app
  %(prog)s my-cli --type cli --author "Jane Doe"
  %(prog)s my-lib --type lib --description "My library"
  %(prog)s quick-test --type app --no-venv --no-git --no-docs
  %(prog)s --interactive
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
    # Project type
    parser.add_argument(
        "--type",
        choices=["app", "cli", "lib"],
        default=None,
        help="Project type: app, cli, or lib (default: lib)",
    )
    # Docs
    parser.add_argument(
        "--no-docs",
        action="store_true",
        help="Do not generate documentation files (README.md, LICENSE, pyproject.toml, .gitignore). Project will not be buildable with uv/hatchling until you add the required files.",
    )
    # Metadata
    parser.add_argument(
        "--description",
        default=None,
        help="Project description for README and pyproject.toml (default: Add your description here)",
    )
    parser.add_argument(
        "--author",
        default="Onehand-Coding",
        help="Author name for LICENSE and pyproject.toml (default: Onehand-Coding)",
    )
    parser.add_argument(
        "--email",
        default="onehand.coding433@gmail.com",
        help="Author email for pyproject.toml (default: onehand.coding433@gmail.com)",
    )
    parser.add_argument(
        "--license-type",
        choices=["MIT", "Apache-2.0", "GPL-3.0"],
        default=None,
        help="License type for documentation files (default: MIT)",
    )
    # Environment
    parser.add_argument(
        "--no-venv", action="store_true", help="Skip virtual environment creation"
    )
    # Git
    parser.add_argument(
        "--no-git", action="store_true", help="Skip Git repository initialization"
    )
    # IDE
    parser.add_argument(
        "--open", "-o", action="store_true", help="Open in Sublime Text after creation"
    )
    # Interactive
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt interactively for all project options.",
    )
    args = parser.parse_args()

    # Interactive prompts
    if args.interactive:
        args.name = prompt_if_missing(args.name, "Project name")
        args.type = prompt_if_missing(
            args.type, "Project type", default="lib", choices=["app", "cli", "lib"]
        )
        args.description = prompt_if_missing(
            args.description, "Project description", default="Add your description here"
        )
        args.author = prompt_if_missing(args.author, "Author name", default="Onehand-Coding")
        args.email = prompt_if_missing(
            args.email, "Author email", default="onehand.coding433@gmail.com"
        )
        args.license_type = prompt_if_missing(
            args.license_type,
            "License type",
            default="MIT",
            choices=["MIT", "Apache-2.0", "GPL-3.0"],
        )
        args.no_docs = (
            prompt_if_missing(
                args.no_docs,
                "Skip documentation generation? (y/N)",
                default="n",
                choices=["y", "n"],
            )
            == "y"
        )
        args.no_venv = (
            prompt_if_missing(
                args.no_venv,
                "Skip virtual environment creation? (y/N)",
                default="n",
                choices=["y", "n"],
            )
            == "y"
        )
        args.no_git = (
            prompt_if_missing(
                args.no_git,
                "Skip Git repository initialization? (y/N)",
                default="n",
                choices=["y", "n"],
            )
            == "y"
        )
        args.open = (
            prompt_if_missing(
                args.open,
                "Open in Sublime Text after creation? (y/N)",
                default="n",
                choices=["y", "n"],
            )
            == "y"
        )
        if not args.path:
            args.path = prompt_if_missing(
                None, "Project path", default=DEFAULT_PROJECTS_DIR
            )

    # Validate arguments
    validate_args(args)

    project_name = args.name
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

    # Determine project type
    is_app = args.type == "app"
    is_cli = args.type == "cli"
    use_src_layout = args.type in ("cli", "lib")

    # Always create the basic project structure
    create_project_files(project_name, package_name, is_app, is_cli, use_src_layout)
    create_gitignore()
    create_sublime_project(project_name)

    if args.no_docs:
        logger.warning(
            "Skipping documentation generation. Project will not be buildable with uv/hatchling until you add the required files."
        )
        # Do NOT create pyproject.toml, README.md, LICENSE, or run setup_dependencies
    else:
        # Create all docs and pyproject.toml
        create_readme(project_name, package_name, args.description, args.license_type)
        create_license_file(args.license_type, args.author)
        create_pyproject_toml(
            project_name,
            package_name,
            use_src_layout,
            is_app,
            is_cli,
            True,  # always has_readme
            args.description,
            args.license_type,
            args.author,
            args.email,
        )
        # Set up environment and dependencies
        setup_dependencies(create_venv)

    # Initialize Git repository
    init_git_repo(args.no_git)

    logger.info(
        f"\n✅ Project '{project_name}' created successfully at {full_project_path}"
    )

    # Print next steps
    logger.info("\nNext steps:")
    logger.info(f"1. cd {full_project_path}")
    if not args.no_docs and create_venv:
        logger.info(
            "2. source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate"
        )
        if is_app:
            logger.info("3. python app.py")
        elif is_cli:
            logger.info(f"3. {project_name}")
        else:
            logger.info("3. Start coding!")
    else:
        if is_app:
            logger.info("2. python app.py")
        else:
            logger.info("2. Start coding!")

    # Handle Sublime Text opening
    if args.open:
        open_in_sublime(str(full_project_path))


if __name__ == "__main__":
    main()
