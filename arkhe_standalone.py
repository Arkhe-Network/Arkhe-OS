#!/usr/bin/env python3
"""
Arkhe OS Standalone Substrate Integrator
This script acts as a single entry point to dynamically load and run
any of the Arkhe OS substrates, providing a unified CLI.
"""
import argparse
import glob
import importlib.util
import os
import sys

def load_substrate(filepath):
    module_name = os.path.basename(filepath)[:-3]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        try:
            # We catch exceptions to prevent one bad substrate from crashing the loader
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            print(f"Warning: Failed to load {module_name}: {e}")
            return None
    return None

def main():
    parser = argparse.ArgumentParser(
        description="Arkhe OS Standalone Substrate Integrator",
        epilog="Integrates multiple substrates into a single manageable CLI."
    )
    parser.add_argument("--list", action="store_true", help="List all available substrates")
    parser.add_argument("--run", type=str, metavar="SUBSTRATE", help="Run a specific substrate (by module name)")
    parser.add_argument("--test-all", action="store_true", help="Test loading all substrates")

    args = parser.parse_args()

    # Locate all substrato_*.py files in the current directory
    substrate_files = sorted(glob.glob("substrato_*.py"))
    # Exclude problematic/unbuildable ones as per repository conventions
    substrate_files = [f for f in substrate_files if "unbuildable" not in f and "fallback" not in f]

    if args.list:
        print("Available Substrates:")
        for f in substrate_files:
            print(f" - {os.path.basename(f)[:-3]}")
        return

    if args.run:
        target = f"{args.run}.py"
        if target in substrate_files:
            print(f"Running {args.run}...")
            mod = load_substrate(target)
            if mod:
                # If the module has a main() function, run it
                if hasattr(mod, "main") and callable(mod.main):
                    mod.main()
                # Or if it has run() function
                elif hasattr(mod, "run") and callable(mod.run):
                    mod.run()
                else:
                    print(f"Substrate {args.run} loaded successfully, but no main() or run() function found.")
        else:
            print(f"Error: Substrate {args.run} not found.")

    if args.test_all:
        success = 0
        failed = 0
        for f in substrate_files:
            if load_substrate(f) is not None:
                success += 1
            else:
                failed += 1
        print(f"\nTested {len(substrate_files)} substrates: {success} succeeded, {failed} failed to load.")

    if not args.list and not args.run and not args.test_all:
        parser.print_help()

if __name__ == "__main__":
    main()
