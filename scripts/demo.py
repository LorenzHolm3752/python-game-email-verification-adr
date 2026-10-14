import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.verification_service import demo


if __name__ == "__main__":
    demo()
