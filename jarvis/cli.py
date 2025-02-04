"""
JARVIS CLI entry point
"""
from .core import main as jarvis_main

def main():
    """Entry point for the jarvis command"""
    try:
        jarvis_main()
    except KeyboardInterrupt:
        print("\nJARVIS terminated by user")
    except Exception as e:
        print(f"\nError running JARVIS: {e}")
        raise

if __name__ == "__main__":
    main()
