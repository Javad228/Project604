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
from pathlib import Path
from typing import Dict, Any
import numpy as np # Needed for average utility calculation
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

    # --- Update params based on CLI flags ---
    # Ensure plotting flag overrides config
    if args.plot:
        params.outputs.save_plots = True
        print("Plot generation enabled via command line flag.")
    elif not hasattr(params.outputs, 'save_plots'): # Handle case where param might be missing
        print("Warning: 'outputs.save_plots' not found in config, defaulting to False.")
        params.outputs.save_plots = False

    # Apply overrides
    if overrides:
        params.update_from_dict(overrides)
    
    # Print simulation parameters
    print("\nSimulation Setup:")
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
    
    # --- Optimization Loop --- 
    print("\nFinding optimal number of cycles...")
    cycle_len_days = 14
    horizon_days = params.optimization.horizon_days
    max_possible_cycles = int(horizon_days // cycle_len_days) # Floor division
    
    best_avg_utility = -np.inf # Initialize with a very low value
    optimal_cycle_count = 0
    best_results = None # Store results for the best cycle count

    for n_cycles in range(max_possible_cycles + 1): # Test from 0 to max_possible_cycles
        print(f"  Simulating with {n_cycles} cycles...")
        try:
            # Instantiate model inside loop if parameters affect initialization beyond BSA
            # (Currently, they don't significantly, so could optimize later if slow)
            model = FOLFOXModel(params)
            results = model.solve(num_cycles_to_administer=n_cycles)
            
            # Calculate average utility (excluding t=0)
            avg_utility = np.mean(results['utility'][1:]) if len(results['utility']) > 1 else params.utility.baseline_utility
            print(f"    Average Utility: {avg_utility:.4f}")

            if avg_utility > best_avg_utility:
                best_avg_utility = avg_utility
                optimal_cycle_count = n_cycles
                best_results = results # Save the full results dict for the best case
                
        except Exception as e:
            print(f"    Error during simulation for {n_cycles} cycles: {e}")
            # Decide how to handle errors: stop, continue, etc.
            # For now, we'll just report and continue searching
            # import traceback
            # traceback.print_exc()

    if best_results is None:
         print("\nError: No successful simulations completed. Cannot determine optimum.", file=sys.stderr)
         return 1
         
    print(f"\nOptimization finished. Optimal number of cycles: {optimal_cycle_count} (Avg Utility: {best_avg_utility:.4f})")

    # --- Final Analysis using Optimal Results --- 
    print("Analyzing results for optimal cycle count...")
    output_dir = Path(params.outputs.results_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Instantiate the analyzer with the best results
        analyzer = FOLFOXAnalyzer(params, best_results)
        # Call the analyze method which handles saving files/plots
        # Plotting is controlled by params.outputs.save_plots inside the analyze method
        analysis_dict = analyzer.analyze() 
        print(f"Optimal results saved to {output_dir}")
    except Exception as e:
        print(f"Error during final results analysis or saving: {e}", file=sys.stderr)
        # import traceback
        # traceback.print_exc()
        return 1

    # Print summary from the dictionary returned by analyze
    if "summary" in analysis_dict:
         try:
             summary = analysis_dict["summary"]
             print("\nOptimal Results Summary:")
             print(f"  Optimal Cycles Run: {optimal_cycle_count}") 
             print(f"  Min ANC: {summary.get('min_anc', 'N/A'):.2f}")
             print(f"  Cumulative Oxaliplatin: {summary.get('cumulative_ox', 'N/A'):.2f} mg")
             print(f"  Chronic Neuropathy Threshold: {summary.get('chronic_neuropathy_threshold_mg', 'N/A'):.2f} mg")
             print(f"  Chronic Neuropathy Onset Day: {summary.get('chronic_neuropathy_onset_day', 'N/A')}")
             print(f"  Final Utility: {summary.get('final_utility', 'N/A'):.2f}")
             print(f"  Mean Utility: {summary.get('mean_utility', 'N/A'):.4f}")
             print(f"  Total Cost: ${summary.get('total_cost', 'N/A'):.2f}")
             print(f"  Mean Daily Cost: ${summary.get('mean_daily_cost', 'N/A'):.2f}")
         except Exception as e:
              print(f"\nError processing summary dictionary: {e}", file=sys.stderr)
    else:
         print("\nSummary data not found in analysis results dictionary.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
