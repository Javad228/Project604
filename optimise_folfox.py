#!/usr/bin/env python
"""
Optimal FOLFOX Scheduler - CLI Entry Point

Simulate FOLFOX therapy effects with one command.
This tool builds and runs a simulation model that predicts daily
5-fluorouracil (5-FU) infusion rates and bi-weekly oxaliplatin doses for a
180-day FOLFOX course.
"""
import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

from params import FOLFOXParams
from model import FOLFOXModel
from analyse import FOLFOXAnalyzer


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Optimal FOLFOX Scheduler - Simulate FOLFOX therapy effects",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Config file
    parser.add_argument(
        "-c", "--config", 
        help="Path to custom configuration YAML file"
    )
    
    # Simulation parameters
    parser.add_argument(
        "--horizon", type=int,
        help="Treatment horizon in days (overrides config)"
    )
    parser.add_argument(
        "--step", type=int,
        help="Step size for discretization in days (overrides config)"
    )
    
    # Output options
    parser.add_argument(
        "--output", "-o", default="results",
        help="Directory for output files"
    )
    parser.add_argument(
        "--plot", action="store_true",
        help="Generate plots of results"
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point for the application."""
    args = parse_args()
    
    # Load parameters
    try:
        params = FOLFOXParams.load(args.config)
        print(f"Loaded parameters{'from ' + args.config if args.config else ''}")
    except Exception as e:
        print(f"Error loading parameters: {e}")
        return 1
    
    # Apply command line overrides
    overrides = {}
    
    if args.horizon:
        overrides.setdefault("optimization", {})["horizon_days"] = args.horizon
    if args.step:
        overrides.setdefault("optimization", {})["step_size_days"] = args.step
    if args.output:
        overrides.setdefault("outputs", {})["results_dir"] = args.output
    if args.plot:
        overrides.setdefault("outputs", {})["save_plots"] = True
    
    # Apply overrides
    if overrides:
        params.update_from_dict(overrides)
    
    # Print simulation parameters
    print(f"Simulation parameters:")
    print(f"  Horizon: {params.optimization.horizon_days} days")
    print(f"  Step size: {params.optimization.step_size_days} days")
    
    # Build and run model
    print("\nBuilding simulation model...")
    model = FOLFOXModel(params)
    
    print("Running simulation...")
    try:
        results = model.solve()
    except Exception as e:
        print(f"Error running simulation: {e}")
        return 1
    
    # Analyze results
    print("\nAnalyzing results...")
    analyzer = FOLFOXAnalyzer(params, results)
    analysis = analyzer.analyze()
    
    # Print summary
    print("\nSimulation Results Summary:")
    print(f"  Cumulative oxaliplatin: {analysis['summary'].get('cumulative_ox', 'N/A'):.1f} mg")
    
    print(f"\nResults saved to {params.outputs.results_dir}/")
    if params.outputs.save_plots:
        print(f"Plots generated:")
        for plot in analysis['plots']:
            print(f"  {Path(plot).name}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
