"""
parse_identity.py - Single-parser identity extraction for LLM-Wiki pipeline.

This is the ONLY component that parses frontmatter. All other components
import this module or shell out to it. No duplicate regex exists anywhere
in the pipeline. (P0-1)

Exit codes:
    0 - Success (valid frontmatter extracted)
    4 - SYSTEM_FAULT (validation failure or infrastructure error)
"""

import json
import os
import re
import sys

from yaml import safe_load, YAMLError

# --- Constants ---

SOURCE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9-]{1,36}$')
MAX_FRONTMATTER_VALUE_BYTES = 256
EXIT_SUCCESS = 0
EXIT_SYSTEM_FAULT = 4
FRONTMATTER_DELIMITER = '---'


def extract_frontmatter(file_path, repo_root=None):
    """Extract YAML frontmatter from the beginning of a file.

    Reads the file with utf-8-sig encoding to transparently handle BOM.
    Only parses the first YAML block (between opening and closing '---').

    Args:
        file_path: Absolute or relative path to the markdown file.
        repo_root: Optional absolute path to the repository root.
                   When provided, file_path is resolved relative to this
                   root, producing deterministic repo-relative identity
                   regardless of the caller's working directory.

    Returns:
        dict with keys:
            source_id (str or None)
            frontmatter_valid (bool)
            frontmatter (dict or None) - sanitized frontmatter values
            error (str or None)
            file_path (str) - repo-relative path
    """
    repo_relative = _to_repo_relative(file_path, repo_root=repo_root)
    result = {
        'source_id': None,
        'frontmatter_valid': False,
        'frontmatter': None,
        'error': None,
        'file_path': repo_relative,
    }

    try:
        with open(file_path, encoding='utf-8-sig') as f:
            content = f.read()
    except (OSError, UnicodeDecodeError) as e:
        result['error'] = 'Failed to read file: {}'.format(str(e))
        return result

    if not content.strip():
        result['error'] = 'File is empty'
        return result

    lines = content.split('\n')

    # First non-empty line must be '---'
    first_line = lines[0].strip()
    if first_line != FRONTMATTER_DELIMITER:
        result['error'] = 'No frontmatter delimiter at beginning of file'
        return result

    # Find the closing '---'
    closing_index = None
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONTMATTER_DELIMITER:
            closing_index = i
            break

    if closing_index is None:
        result['error'] = 'No closing frontmatter delimiter found'
        return result

    yaml_block = '\n'.join(lines[1:closing_index])

    try:
        parsed = safe_load(yaml_block)
    except YAMLError as e:
        result['error'] = 'YAML parse error: {}'.format(str(e))
        return result

    if not isinstance(parsed, dict):
        result['error'] = 'Frontmatter is not a YAML mapping'
        return result

    # Validate source_id presence and reject explicit null/None
    if 'source_id' not in parsed:
        result['error'] = 'Missing required field: source_id'
        return result

    if parsed['source_id'] is None:
        result['error'] = 'source_id is null'
        return result

    source_id = str(parsed['source_id'])

    # Validate source_id format (P0-10)
    valid, reason = validate_source_id(source_id)
    if not valid:
        result['error'] = reason
        return result

    # Sanitize all values (256-byte cap)
    sanitized = sanitize_frontmatter_values(parsed)

    result['source_id'] = source_id
    result['frontmatter_valid'] = True
    result['frontmatter'] = sanitized
    return result


def validate_source_id(source_id):
    """Validate source_id against restricted identifier format.

    Pattern: ^[a-zA-Z0-9-]{1,36}$
    This is NOT a UUID regex - it accepts any alphanumeric + hyphen string
    up to 36 characters. (P0-10)

    Args:
        source_id: The source_id string to validate.

    Returns:
        Tuple of (is_valid: bool, error_reason: str or None)
    """
    if not isinstance(source_id, str):
        return False, 'source_id must be a string, got {}'.format(type(source_id).__name__)

    if not SOURCE_ID_PATTERN.match(source_id):
        if len(source_id) > 36:
            return False, 'source_id exceeds 36 characters (got {})'.format(len(source_id))
        if len(source_id) == 0:
            return False, 'source_id is empty'
        return False, "source_id '{}' does not match ^[a-zA-Z0-9-]{{1,36}}$".format(source_id)

    return True, None


def sanitize_frontmatter_values(parsed):
    """Enforce 256-byte cap on all frontmatter values.

    Converts all values to strings and truncates any that exceed
    MAX_FRONTMATTER_VALUE_BYTES when encoded as UTF-8.

    Args:
        parsed: Dict of parsed YAML frontmatter.

    Returns:
        Dict with all values as strings, truncated to 256 bytes.
    """
    sanitized = {}
    for key, value in parsed.items():
        str_value = str(value)
        encoded = str_value.encode('utf-8')
        if len(encoded) > MAX_FRONTMATTER_VALUE_BYTES:
            # Truncate at byte boundary, decode safely
            truncated = encoded[:MAX_FRONTMATTER_VALUE_BYTES]
            str_value = truncated.decode('utf-8', errors='ignore')
        sanitized[str(key)] = str_value
    return sanitized


def _to_repo_relative(file_path, repo_root=None):
    """Convert an absolute path to a repo-relative path.

    Uses forward slashes for consistency across platforms.

    When repo_root is provided, the path is resolved relative to that
    root — producing a deterministic, cwd-independent result.  This is
    the preferred mode for production use (TD-003).

    When repo_root is omitted, falls back to os.path.relpath() from cwd
    for backward compatibility with existing callers.
    """
    abs_path = os.path.abspath(file_path)

    if repo_root is not None:
        root = os.path.abspath(repo_root)
        # Normalise so the prefix check works on all platforms
        if not root.endswith(os.sep):
            root = root + os.sep
        if not abs_path.startswith(root):
            # File is outside repo root — return the absolute path as-is
            # rather than silently producing a misleading relative path.
            return abs_path.replace('\\', '/')
        return abs_path[len(root):].replace('\\', '/')

    # Legacy fallback: cwd-relative (non-deterministic)
    try:
        rel = os.path.relpath(abs_path)
    except ValueError:
        # On Windows, relpath fails across drives
        rel = abs_path
    return rel.replace('\\', '/')


def main(argv=None):
    """CLI entry point.

    Usage: python parse_identity.py <file_path> [--repo-root <path>]

    Prints exactly one JSON object to stdout.
    Exits 0 on success, 4 on validation failure.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Single-parser identity extraction for LLM-Wiki pipeline"
    )
    parser.add_argument(
        "file_path",
        type=str,
        help="Path to the markdown file to parse",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Absolute path to the repository root. When provided, "
             "file_path is resolved relative to this root for "
             "deterministic repo-relative identity.",
    )
    args = parser.parse_args(argv)

    file_path = args.file_path
    repo_root = args.repo_root

    if not os.path.isfile(file_path):
        error_result = {
            'source_id': None,
            'frontmatter_valid': False,
            'frontmatter': None,
            'error': 'File not found: {}'.format(file_path),
            'file_path': file_path,
        }
        print(json.dumps(error_result))
        sys.exit(EXIT_SYSTEM_FAULT)

    result = extract_frontmatter(file_path, repo_root=repo_root)
    print(json.dumps(result))

    if result['frontmatter_valid']:
        sys.exit(EXIT_SUCCESS)
    else:
        sys.exit(EXIT_SYSTEM_FAULT)


if __name__ == '__main__':
    main()
