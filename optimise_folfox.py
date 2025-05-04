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
import math

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
    
    # Patient specifics
    parser.add_argument(
        "--weight", type=float, default=None,
        help="Patient weight in kg (overrides config)"
    )
    parser.add_argument(
        "--height", type=float, default=None,
        help="Patient height in cm (overrides config)"
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
    
    # Apply patient specifics overrides
    if args.weight is not None:
        if args.weight <= 0:
             print("Error: Patient weight must be positive.", file=sys.stderr)
             return 1
        overrides.setdefault("dosing", {})["patient_weight_kg"] = args.weight
        print(f"Overriding patient weight to: {args.weight} kg")
    if args.height is not None:
        if args.height <= 0:
             print("Error: Patient height must be positive.", file=sys.stderr)
             return 1
        overrides.setdefault("dosing", {})["patient_height_cm"] = args.height
        print(f"Overriding patient height to: {args.height} cm")
    
    # Apply overrides
    if overrides:
        params.update_from_dict(overrides)
    
    # Print simulation parameters
    print(f"Simulation parameters:")
    print(f"  Horizon: {params.optimization.horizon_days} days")
    print(f"  Step size: {params.optimization.step_size_days} days")
    
    # Calculate and print BSA based on potentially overridden values
    try:
         weight_kg = params.dosing.patient_weight_kg
         height_cm = params.dosing.patient_height_cm
         bsa = math.sqrt((height_cm * weight_kg) / 3600.0)
         print(f"  Patient Weight: {weight_kg} kg")
         print(f"  Patient Height: {height_cm} cm")
         print(f"  Calculated BSA: {bsa:.2f} m^2")
    except Exception as e:
         print(f"Could not calculate BSA: {e}") # Should not happen with checks above
    
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
