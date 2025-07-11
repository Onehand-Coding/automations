#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
from typing import Optional
from datetime import datetime

from helper import setup_logging, confirm
from helper.templates import (
    LICENSE_TEMPLATES,
    README_TEMPLATE,
    PYPROJECT_TEMPLATE,
    GITIGNORE_TEMPLATE,
)

logger = setup_logging(log_file="docs_generator.log")


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
