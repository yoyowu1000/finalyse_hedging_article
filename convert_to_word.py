#!/usr/bin/env python3
"""
Convert finalyse_hedging_article.md to Word document using pandoc.
"""

import subprocess
import sys
from pathlib import Path


def convert_markdown_to_word(input_file: str, output_file: str = None) -> None:
    """
    Convert a markdown file to Word document using pandoc.
    
    Args:
        input_file: Path to the markdown file
        output_file: Path to the output Word file (optional)
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    
    if output_file is None:
        output_file = input_path.stem + ".docx"
    
    # Build pandoc command
    cmd = [
        "pandoc",
        str(input_path),
        "-o", output_file,
        "--from", "markdown",
        "--to", "docx",
        "--standalone",
        "--toc",  # Add table of contents
        "--toc-depth=2",  # TOC depth
        "--highlight-style", "tango",  # Code highlighting style
        "--reference-doc=reference.docx" if Path("reference.docx").exists() else "",
    ]
    
    # Remove empty strings from command
    cmd = [arg for arg in cmd if arg]
    
    print(f"Converting '{input_file}' to '{output_file}'...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Successfully converted to '{output_file}'")
        else:
            print("Error: Conversion failed")
            if result.stderr:
                print(f"Error details: {result.stderr}")
            sys.exit(1)
            
    except FileNotFoundError:
        print("Error: pandoc not found. Please install pandoc:")
        print("  - macOS: brew install pandoc")
        print("  - Ubuntu/Debian: sudo apt-get install pandoc")
        print("  - Windows: Download from https://pandoc.org/installing.html")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main function to convert the article."""
    # Define file paths
    input_file = "finalyse_hedging_article.md"
    output_file = "finalyse_hedging_article.docx"
    
    # Check if we're in the right directory
    if not Path(input_file).exists():
        print(f"Error: '{input_file}' not found in current directory.")
        print("Please run this script from the hedging_article directory.")
        sys.exit(1)
    
    # Convert the file
    convert_markdown_to_word(input_file, output_file)
    
    # Additional conversions if needed
    print("\nYou can also convert to other formats:")
    print(f"  PDF: pandoc {input_file} -o finalyse_hedging_article.pdf")
    print(f"  HTML: pandoc {input_file} -o finalyse_hedging_article.html --self-contained")


if __name__ == "__main__":
    main()