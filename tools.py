"""
Minimal local file tools for an LLM agent.

Four tools: write_file, read_file, list_files, search_files.
Files live in <script_dir>/files (created automatically, absolute path
so it doesn't depend on what directory you launched python from).

Supports subfolders, e.g. filename="recipes/pasta.md" -> files/recipes/pasta.md

search_files checks filenames first (cheap), and only scans file
contents if no filename matched -- saves tokens/time on most searches.
"""

import os

# absolute path based on where this script lives, not the current working
# directory -- fixes "files seem to disappear" when run from different folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "files")
os.makedirs(FILES_DIR, exist_ok=True)

# extensions allowed for read/write -- covers common text + code file types
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".json", ".csv", ".log",
    ".py", ".js", ".ts", ".html", ".css", ".sh", ".yaml", ".yml",
}

# ---- tool schemas (what we tell the model is available) ----

TOOLS = [
    {
        "name": "write_file",
        "description": (
            "Write text content to a local file. Overwrites if it already exists. "
            "Subfolders are supported, e.g. 'recipes/pasta.md'. "
            f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "e.g. 'notes.txt', 'script.py', or 'recipes/pasta.md'",
                },
                "content": {"type": "string", "description": "Text to write"},
            },
            "required": ["filename", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the text content of a local file. Supports subfolder paths.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
            },
            "required": ["filename"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files currently saved locally, including subfolders.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_files",
        "description": (
            "Search for files by query. Matches filenames first (cheap); "
            "only scans file contents if no filename matches are found."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to search for"},
            },
            "required": ["query"],
        },
    },
]


# ---- tool implementations (what actually runs when the model calls a tool) ----

def _safe_path(filename: str) -> str:
    """Resolve filename (which may include subfolders) under FILES_DIR,
    blocking path traversal like '../../etc/passwd'."""
    # normalize separators and strip any leading slashes
    filename = filename.replace("\\", "/").lstrip("/")
    candidate = os.path.normpath(os.path.join(FILES_DIR, filename))

    # ensure the resolved path is still inside FILES_DIR
    if not candidate.startswith(os.path.abspath(FILES_DIR) + os.sep) and candidate != FILES_DIR:
        raise ValueError(f"invalid path: {filename}")

    return candidate


def _check_extension(filename: str) -> str | None:
    """Returns an error string if extension isn't allowed, else None."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"error: extension '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    return None


def _list_all_files() -> list[str]:
    """List files recursively, returned as paths relative to FILES_DIR
    using forward slashes (e.g. 'recipes/pasta.md')."""
    results = []
    for root, _dirs, files in os.walk(FILES_DIR):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, FILES_DIR).replace(os.sep, "/")
            results.append(rel)
    return results


def run_tool(name: str, tool_input: dict) -> str:
    if name == "write_file":
        filename = tool_input["filename"]
        err = _check_extension(filename)
        if err:
            return err
        try:
            path = _safe_path(filename)
        except ValueError as e:
            return f"error: {e}"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(tool_input["content"])
        return f"wrote {len(tool_input['content'])} chars to {filename}"

    elif name == "read_file":
        filename = tool_input["filename"]
        err = _check_extension(filename)
        if err:
            return err
        try:
            path = _safe_path(filename)
        except ValueError as e:
            return f"error: {e}"
        if not os.path.exists(path):
            return f"error: {filename} not found"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    elif name == "list_files":
        files = _list_all_files()
        return ", ".join(files) if files else "(no files yet)"

    elif name == "search_files":
        query = tool_input["query"].lower()
        all_files = _list_all_files()

        # 1. filename match first -- cheap, no disk reads
        filename_matches = [f for f in all_files if query in f.lower()]
        if filename_matches:
            return f"filename matches: {', '.join(filename_matches)}"

        # 2. fall back to content scan only if no filename matched
        content_matches = []
        for f in all_files:
            path = os.path.join(FILES_DIR, f)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    if query in fh.read().lower():
                        content_matches.append(f)
            except (UnicodeDecodeError, OSError):
                continue  # skip unreadable files

        if content_matches:
            return f"content matches: {', '.join(content_matches)}"
        return "no matches found"

    else:
        return f"error: unknown tool {name}"