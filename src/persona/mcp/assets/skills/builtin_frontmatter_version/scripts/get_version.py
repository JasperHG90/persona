# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-frontmatter>=1.1.0",
# ]
# ///

import frontmatter
import json
import argparse
from typing import cast
from pathlib import Path

def extract_version(file_path):
    try:
        path = Path(file_path)
        if not path.exists():
            return {"status": "error", "message": f"File not found: {file_path}"}
        
        # Load the markdown file
        post = frontmatter.load(file_path)
        
        # Extract version
        version = cast(dict[str, str], post.metadata["metadata"]).get("version")
        
        if version:
            return {
                "status": "success",
                "file": path.name,
                "version": str(version)
            }
        else:
            return {
                "status": "missing_tag",
                "message": "The file contains frontmatter but no 'version' tag was found.",
                "metadata_keys": list(post.keys())
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract version from MD frontmatter.")
    parser.add_argument("file", help="Path to the markdown file")
    args = parser.parse_args()

    result = extract_version(args.file)
    print(json.dumps(result, indent=2))
