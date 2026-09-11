import sys
from pathlib import Path

# Add the parent directory of packager to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packager.app import main

if __name__ == "__main__":
    main()
