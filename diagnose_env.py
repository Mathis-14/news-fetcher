import sys
print("Python Executable:", sys.executable)
print("Python Path:", sys.path)

try:
    from bs4 import BeautifulSoup
    print("BeautifulSoup is available")
except ImportError as e:
    print(f"Error importing BeautifulSoup: {e}")

try:
    import yaml
    print("PyYAML is available")
except ImportError as e:
    print(f"Error importing PyYAML: {e}")

try:
    import requests
    print("Requests is available")
except ImportError as e:
    print(f"Error importing Requests: {e}")