"""
Analysis and visualization module for FOLFOX simulation results.
Handles plotting results and exporting data to CSV.
"""
from pathlib import Path
import json
import csv
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from params import FOLFOXParams


class FOLFOXAnalyzer:
    """Analyzer for FOLFOX simulation results."""
    
    def __init__(self, params: FOLFOXParams, results: Dict[str, Any]):
        """Initialize with parameters and simulation results."""
        self.params = params
        self.results = results # Expects keys: time, dose_5fu, dose_ox, anc, acute_neuropathy, chronic_neuropathy, cum_ox, utility
        self.output_dir = Path(params.outputs.results_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_csv(self) -> Path:
        """Export simulation results to CSV file."""
        csv_path = self.output_dir / "simulation_results.csv"
        
        # Prepare data - assuming keys exist in self.results
        data = {
            "Day": self.results["time"],
            "5FU_Dose_mg": self.results["dose_5fu"],
            "Oxaliplatin_Dose_mg": self.results["dose_ox"],
            # Removed PK concentrations
            # Removed Tumor Volume
            "ANC_10^9_L": self.results["anc"],
            # Removed Neuropathy_Grade
            "Acute_Neuropathy(0/1)": self.results["acute_neuropathy"],
            "Chronic_Neuropathy(0/1)": self.results["chronic_neuropathy"],
            "Cumulative_Oxaliplatin_mg": self.results["cum_ox"],
            "Utility": self.results["utility"]
        }
        
        # Create DataFrame and export
        df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False)
        
        print(f"CSV results exported to {csv_path}")
        return csv_path
    
    def export_summary(self, summary: Dict[str, Any]) -> Path: # Pass summary in
        """Export summary statistics to JSON file."""
        json_path = self.output_dir / "summary.json"
        
        # Basic type conversion for JSON compatibility
        summary_serializable = {k: (float(v) if isinstance(v, np.floating) else 
                                   int(v) if isinstance(v, np.integer) else 
                                   v) 
                              for k, v in summary.items()}

        with open(json_path, "w") as f:
            json.dump(summary_serializable, f, indent=2)
        
        print(f"Summary exported to {json_path}")
        return json_path
    
    def plot_anc(self) -> Figure:
        """Plot ANC and doses over time."""
        time = self.results["time"]
        anc = self.results["anc"]
        doses_5fu = self.results["dose_5fu"]
        doses_ox = self.results["dose_ox"]
        
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        # Plot ANC
        color = 'tab:blue'
        ax1.set_xlabel("Time (days)")
        ax1.set_ylabel("ANC (10⁹/L)", color=color)
        ax1.plot(time, anc, color=color, linewidth=2)
        ax1.tick_params(axis='y', labelcolor=color)
        # Use severe_neutropenia_threshold for the critical line
        crit_thresh = self.params.hematology.severe_neutropenia_threshold
        ax1.axhline(y=crit_thresh, color='r', linestyle='--', 
                   label=f"Severe Neutropenia ({crit_thresh:.1f})")
        
        # Plot doses on secondary y-axis
        ax2 = ax1.twinx()
        color_5fu = 'tab:green'
        color_ox = 'tab:orange'
        
        ax2.set_ylabel("Dose (mg)", color='black')
        
        # Plot 5-FU doses as bars
        ax2.bar([time[i] for i in range(len(time) - 1) if doses_5fu[i] > 0],
               [doses_5fu[i] for i in range(len(time) - 1) if doses_5fu[i] > 0],
               width=1.0, alpha=0.3, color=color_5fu, label='5-FU Dose')
        
        # Plot oxaliplatin doses as points
        ax2.scatter([time[i] for i in range(len(time) - 1) if doses_ox[i] > 0],
                   [doses_ox[i] for i in range(len(time) - 1) if doses_ox[i] > 0],
                   color=color_ox, s=80, marker='d', label='Oxaliplatin Dose')
        
        ax2.tick_params(axis='y', labelcolor='black')
        
        # Add legend and title
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        # Ensure labels2 is not empty before concatenating
        if lines2:
             ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        else:
             ax1.legend(lines1, labels1, loc='upper right')
        
        plt.title("ANC and Dosing Schedule")
        fig_path = self.output_dir / "anc_curve.png"
        plt.tight_layout()
        plt.savefig(fig_path)
        plt.close()
        
        return fig
    
    def plot_neuropathy(self) -> Figure:
        """Plot neuropathy flags and cumulative oxaliplatin dose."""
        time = self.results["time"]
        acute_neuro = self.results["acute_neuropathy"] # Binary flag
        chronic_neuro = self.results["chronic_neuropathy"] # Binary flag
        cum_ox = self.results["cum_ox"]
        threshold = self.results['chronic_neuropathy_threshold_mg'][0] # Get threshold from results
        
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        # Plot neuropathy flags (step plot)
        color_acute = 'tab:purple'
        color_chronic = 'tab:red'
        ax1.set_xlabel("Time (days)")
        ax1.set_ylabel("Neuropathy Status (0=No, 1=Yes)", color='black')
        ax1.step(time, acute_neuro, color=color_acute, linewidth=1.5, where='post', label='Acute Neuropathy')
        ax1.step(time, chronic_neuro, color=color_chronic, linewidth=1.5, where='post', label='Chronic Neuropathy')
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.set_yticks([0, 1]) # Ensure y-axis shows 0 and 1
        ax1.set_ylim(-0.1, 1.1)
        
        # Plot cumulative oxaliplatin on secondary y-axis
        ax2 = ax1.twinx()
        color_ox = 'tab:orange'
        ax2.set_ylabel("Cumulative Oxaliplatin (mg)", color=color_ox)
        ax2.plot(time, cum_ox, color=color_ox, linestyle='--', linewidth=1.5, label='Cumulative Ox')
        ax2.tick_params(axis='y', labelcolor=color_ox)
        
        # Mark absolute threshold
        ax2.axhline(y=threshold, color='grey', linestyle=':', 
                   label=f"Chronic Threshold ({threshold:.0f} mg)")
        
        # Add legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        # Combine legends
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='center left')
        
        plt.title("Neuropathy Status and Cumulative Oxaliplatin")
        fig_path = self.output_dir / "neuropathy_curve.png"
        plt.tight_layout()
        plt.savefig(fig_path)
        plt.close()
        
        return fig
    
    def plot_utility(self) -> Figure:
        """Plot utility (QALY) over time."""
        time = self.results["time"]
        utility = self.results["utility"]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(time, utility, 'g-', linewidth=2)
        ax.set_xlabel("Time (days)")
        ax.set_ylabel("Utility") # Simplified label
        ax.set_title("Utility Over Time")
        ax.grid(True)
        # Optionally add baseline utility line
        ax.axhline(y=self.params.utility.baseline_utility, color='grey', linestyle=':', 
                   label=f"Baseline ({self.params.utility.baseline_utility:.2f})")
        ax.legend(loc='best')
        
        fig_path = self.output_dir / "utility_curve.png"
        plt.tight_layout()
        plt.savefig(fig_path)
        plt.close()
        
        return fig
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze results and generate outputs."""
        analysis_results = {
            "summary": {},
            "csv_path": None,
            "plots": []
        }
        
        # --- Calculate Summary Statistics --- 
        time = np.array(self.results['time'])
        anc = np.array(self.results['anc'])
        utility = np.array(self.results['utility'])
        cum_ox = np.array(self.results['cum_ox'])
        chronic_neuro = np.array(self.results['chronic_neuropathy'])
        
        summary = {}
        summary['cumulative_ox'] = cum_ox[-1] if len(cum_ox) > 0 else 0
        summary['final_anc'] = anc[-1] if len(anc) > 0 else self.params.hematology.anc_baseline
        summary['min_anc'] = np.min(anc) if len(anc) > 0 else self.params.hematology.anc_baseline
        crit_thresh = self.params.hematology.severe_neutropenia_threshold
        summary['days_severe_neutropenia'] = np.sum(anc < crit_thresh) if len(anc) > 0 else 0
        summary['final_utility'] = utility[-1] if len(utility) > 0 else self.params.utility.baseline_utility
        summary['mean_utility'] = np.mean(utility) if len(utility) > 0 else self.params.utility.baseline_utility
        
        # Find onset day for chronic neuropathy
        chronic_flags = self.results['chronic_neuropathy']
        onset_idx = np.where(chronic_flags == 1)[0]
        summary['chronic_neuropathy_onset_day'] = time[onset_idx[0]] if len(onset_idx) > 0 else -1
        # Add threshold used to summary
        summary['chronic_neuropathy_threshold_mg'] = self.results['chronic_neuropathy_threshold_mg'][0]
        
        # Removed tumor, QALY gain, cost calculations
        analysis_results["summary"] = summary
        
        # --- Export Data --- 
        analysis_results["csv_path"] = str(self.export_csv())
        self.export_summary(summary) # Pass calculated summary
        
        # --- Generate Plots --- 
        if self.params.outputs.save_plots:
            plot_paths = []
            # Removed plot_tumor call
            self.plot_anc()
            plot_paths.append(str(self.output_dir / "anc_curve.png"))
            self.plot_neuropathy()
            plot_paths.append(str(self.output_dir / "neuropathy_curve.png"))
            self.plot_utility()
            plot_paths.append(str(self.output_dir / "utility_curve.png"))
            # TODO: Add plot for doses if needed
            analysis_results["plots"] = plot_paths
            
        return analysis_results
