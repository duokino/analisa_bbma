import subprocess
import sys
import time

# List of dependencies from the setup.py
dependencies = [
    "pandas",
    "numpy",
    "MetaTrader5",
    "joblib",
    "xgboost",
    "colorama"
]

# Simple progress bar function
def show_progress_bar(task, total, current):
    bar_length = 50
    progress = int(bar_length * current / total)
    percent = int(100 * current / total)
    bar = "█" * progress + "-" * (bar_length - progress)
    sys.stdout.write(f"\r{task} |{bar}| {percent}%")
    sys.stdout.flush()

# Function to install a single package
def install_package(package, index, total):
    try:
        show_progress_bar(f"Installing {package}", total, index)
        subprocess.check_call([sys.executable, "-m", "pip", "install", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sys.stdout.write("\r" + " " * 120 + "\r")  # Clear the line
        print(f"✅ {package} installed successfully!")
    except subprocess.CalledProcessError:
        print(f"\n❌ Failed to install {package}. Please check for errors.\n")

# Install dependencies with simple progress bar
print(f"\n🚀 Starting dependencies installation...")
for i, package in enumerate(dependencies, start=1):
    install_package(package, i, len(dependencies))

print(f"\n🎉 All dependencies installed successfully!")
