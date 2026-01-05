#!/usr/bin/env python3
"""
Main orchestrator to populate entire database with mock data.
Runs all generation scripts in sequence.
"""
import sys
import os
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def run_script(script_path: str, description: str):
    """Run a Python script and handle errors"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}\n")

    result = subprocess.run([sys.executable, script_path], cwd=os.getcwd())

    if result.returncode != 0:
        print(f"\n❌ {description} failed with return code {result.returncode}")
        sys.exit(1)

    print(f"\n✅ {description} completed successfully!")


def main():
    print("🎯 Starting database population...")
    print("This will generate:")
    print("  - 10-15 suppliers")
    print("  - 500-1000 products with inventory")
    print("  - 50-100 purchase orders (last 3 months)")
    print()

    scripts_dir = os.path.dirname(__file__)

    # Run scripts in order
    run_script(
        os.path.join(scripts_dir, '01_generate_suppliers.py'),
        "Step 1: Generating Suppliers"
    )

    run_script(
        os.path.join(scripts_dir, '02_generate_inventory.py'),
        "Step 2: Generating Inventory"
    )

    run_script(
        os.path.join(scripts_dir, '03_generate_orders.py'),
        "Step 3: Generating Purchase Orders"
    )

    print(f"\n{'='*60}")
    print("🎉 DATABASE POPULATION COMPLETE!")
    print(f"{'='*60}\n")

    print("Next steps:")
    print("  1. Run verification: python src/scripts/verify_data.py")
    print("  2. Start the API: uvicorn main:app --reload")
    print()


if __name__ == '__main__':
    main()
