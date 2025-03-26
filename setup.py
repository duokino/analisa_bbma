import subprocess
import sys
import time
import ensurepip

def show_progress_bar(current, total):
    percent = int(100 * current / total)
    sys.stdout.write(f"\r[{percent}%]...")
    sys.stdout.flush()

def install_package(package, index, total, total_packages):
    try:
        show_progress_bar(index, total_packages)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sys.stdout.write("\r" + " " * 120 + "\r")  # Clear the line
        print(f"✅ {package} installed successfully!")
    except subprocess.CalledProcessError:
        print(f"\n❌ Failed to install {package}. Please check for errors.\n")

# Ensure pip is available
print("\n🔍 Checking for pip...")
try:
    subprocess.check_call([sys.executable, "-m", "pip", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✅ pip is already installed!")
except subprocess.CalledProcessError:
    print("⚠️ pip not found! Attempting to install using ensurepip...")
    ensurepip.bootstrap()
    print("✅ pip installed successfully!")

# Ensure essential packages are up-to-date
essential_packages = ["pip", "setuptools", "wheel"]
dependencies = [
    "pandas",
    "numpy",
    "MetaTrader5",
    "joblib",
    "xgboost",
    "colorama"
]

total_packages = len(essential_packages) + len(dependencies)
print("\n🚀 Ensuring essential packages are up-to-date...")
for i, package in enumerate(essential_packages, start=1):
    install_package(package, i, len(essential_packages), total_packages)

# Install dependencies
print("\n🚀 Starting dependencies installation...")
for i, package in enumerate(dependencies, start=len(essential_packages) + 1):
    install_package(package, i, len(dependencies), total_packages)

print("\n🎉 All dependencies installed successfully!")
