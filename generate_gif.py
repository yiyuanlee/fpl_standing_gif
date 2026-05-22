import sys
from fpl_visualizer import main

if __name__ == "__main__":
    # Default to gif format if not specified
    if "--format" not in sys.argv and "-f" not in sys.argv:
        sys.argv.extend(["--format", "gif"])
    main()
