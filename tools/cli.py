"""Shared helpers for the root ./build and ./patch commands."""
import os,sys
def ask_path(arg):
    """ROM path from the argument or a prompt; accepts drag-and-drop paths (quotes, backslash-escaped spaces, ~)."""
    p=(arg if arg else input('Path to the original Japanese ROM (.ngc): ')).strip()
    if len(p)>1 and p[0]==p[-1] and p[0] in '"\'': p=p[1:-1]
    elif os.sep=='/': p=p.replace('\\ ',' ')
    p=os.path.expanduser(p)
    if not os.path.isfile(p): sys.exit(f'File not found: {p}')
    return os.path.abspath(p)
