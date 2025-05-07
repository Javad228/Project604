"""
Script to run the FOLFOX model and generate utility comparison plots.
"""
import yaml
from pathlib import Path
import matplotlib.pyplot as plt

from params import FOLFOXParams
from model import FOLFOXModel
from analyse import FOLFOXAnalyzer

def main():
    # Load parameters from default config
    config_path = Path("config_default.yml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Create parameters object
    params = FOLFOXParams.from_dict(config)
    
    # Create model
    model = FOLFOXModel(params)
    
    # Run simulation for 6 cycles (standard FOLFOX regimen)
    results = model.simulate(num_cycles_to_administer=6)
    
    # Create analyzer
    analyzer = FOLFOXAnalyzer(params, results)
    
    # Generate and save the utility comparison plot
    analyzer.plot_utility_comparison()
    
    # Also generate other plots for reference
    analyzer.plot_utility()
    analyzer.plot_tumor_size()
    
    print("Plots generated successfully!")

if __name__ == "__main__":
    main()
