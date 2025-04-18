import os
import shutil
from pathlib import Path

def cleanup():
    """Clean up temporary files and create necessary directories"""
    # Directories to clean
    temp_dirs = ['__pycache__', '.pytest_cache', '.mypy_cache']
    
    # Directories to ensure exist
    required_dirs = ['data', 'reports', 'fonts']
    
    # Clean temporary directories
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name in temp_dirs:
                path = Path(root) / dir_name
                print(f"Removing {path}")
                shutil.rmtree(path)
    
    # Create required directories
    for dir_name in required_dirs:
        path = Path(dir_name)
        path.mkdir(exist_ok=True)
        print(f"Ensuring directory exists: {path}")
    
    # Create empty JSON files if they don't exist
    json_files = ['goals.json', 'checklist.json', 'moods.json', 'schedule.json']
    for json_file in json_files:
        path = Path('data') / json_file
        if not path.exists():
            print(f"Creating empty JSON file: {path}")
            path.write_text('[]')

if __name__ == '__main__':
    cleanup()
    print("Cleanup completed successfully!") 