import os
import os.path
from pathlib import Path

# Set a dedicated folder for file I/O
working_directory = "auto_gpt_workspace"

if not os.path.exists(working_directory):
    os.makedirs(working_directory)


def safe_join(base, *paths):
    root = Path(base).resolve()
    resolved = root.joinpath(*paths).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Attempted to access outside of working directory.")
    return str(resolved)


def read_file(filename):
    try:
        filepath = safe_join(working_directory, filename)
        with open(filepath, "r") as f:
            content = f.read()
        return content
    except Exception as e:
        return "Error: " + str(e)


def write_to_file(filename, text):
    try:
        filepath = safe_join(working_directory, filename)
        directory = os.path.dirname(filepath)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(filepath, "w") as f:
            f.write(text)
        return "File written to successfully."
    except Exception as e:
        return "Error: " + str(e)


def append_to_file(filename, text):
    try:
        filepath = safe_join(working_directory, filename)
        with open(filepath, "a") as f:
            f.write(text)
        return "Text appended successfully."
    except Exception as e:
        return "Error: " + str(e)


def delete_file(filename):
    try:
        filepath = safe_join(working_directory, filename)
        os.remove(filepath)
        return "File deleted successfully."
    except Exception as e:
        return "Error: " + str(e)
