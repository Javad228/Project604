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
        self.results = results # Expects keys: time, dose_5fu, dose_ox, anc, acute_neuropathy, chronic_neuropathy, cum_ox, utility, daily_cost, total_cost
        self.output_dir = Path(params.outputs.results_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Calculate dt from time array for summary statistics
        self.dt = results['time'][1] - results['time'][0] if len(results['time']) > 1 else 1.0
    
    def export_csv(self) -> Path:
        """Export simulation results to CSV file."""
        csv_path = self.output_dir / "simulation_results.csv"
        
        # Prepare data - assuming keys exist in self.results
        data = {
            "Day": self.results["time"],
            "5FU_Dose_mg": self.results["dose_5fu"],
            "Oxaliplatin_Dose_mg": self.results["dose_ox"],
            # Removed PK concentrations
            "Tumor_Size": self.results["tumor_size"],
            "ANC_10^9_L": self.results["anc"],
            # Removed Neuropathy_Grade
            "Acute_Neuropathy(0/1)": self.results["acute_neuropathy"],
            "Chronic_Neuropathy(0/1)": self.results["chronic_neuropathy"],
            "Cumulative_Oxaliplatin_mg": self.results["cum_ox"],
            "Utility": self.results["utility"],
            "Daily_Cost": self.results["daily_cost"], # Added
            "Total_Cost": self.results["total_cost"] # Added
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

    def plot_tumor_size(self) -> Figure:
        """Plot tumor size over time and save to file."""
        time = self.results["time"]
        tumor_size = self.results["tumor_size"]
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(time, tumor_size, color='brown', linewidth=2, label='Tumor Size')
        ax.set_xlabel("Time (days)")
        ax.set_ylabel("Tumor Size (arbitrary units)")
        ax.set_title("Tumor Size Over Time")
        ax.grid(True)
        ax.legend(loc='best')
        fig_path = self.output_dir / "tumor_size_curve.png"
        plt.tight_layout()
        plt.savefig(fig_path)
        plt.close()
        return fig
    
    def analyze(self, generate_plots: bool = None) -> Dict[str, Any]:
        """Perform analysis: export data, calculate summary, generate plots."""
        # Use generate_plots argument if provided, else use param file setting
        if generate_plots is None:
             generate_plots = self.params.outputs.save_plots
             
        analysis_results = {"plots": []}
        
        # Export raw data
        csv_path = self.export_csv()
        analysis_results["csv_export_path"] = str(csv_path)
        
        # Calculate summary statistics
        time = self.results["time"]
        anc = self.results["anc"]
        utility = self.results["utility"]
        chronic_neuro = self.results["chronic_neuropathy"]
        daily_cost = self.results["daily_cost"]
        total_cost = self.results["total_cost"]

        summary = {}
        summary['min_anc'] = np.min(anc)
        summary['cumulative_ox'] = self.results["cum_ox"][-1]
        summary['final_anc'] = anc[-1]
        severe_threshold = self.params.hematology.severe_neutropenia_threshold
        # Calculate days * self.dt
        summary['days_severe_neutropenia'] = np.sum(anc[1:] < severe_threshold) * self.dt 
        summary['final_utility'] = utility[-1]
        # Exclude t=0 from mean utility calculation
        summary['mean_utility'] = np.mean(utility[1:]) if len(utility) > 1 else self.params.utility.baseline_utility 
        chronic_onset_indices = np.where(chronic_neuro > 0.5)[0]
        summary['chronic_neuropathy_onset_day'] = time[chronic_onset_indices[0]] if len(chronic_onset_indices) > 0 else -1
        summary['chronic_neuropathy_threshold_mg'] = self.results['chronic_neuropathy_threshold_mg'][0]
        # Add cost summaries
        summary['total_cost'] = total_cost[-1]
        # Mean daily cost over the days with actual treatment or simulation progress
        summary['mean_daily_cost'] = np.mean(daily_cost) if len(daily_cost) > 0 else 0 

        analysis_results["summary"] = summary
        summary_path = self.export_summary(summary)
        analysis_results["summary_export_path"] = str(summary_path)
        
        # Generate plots if requested
        if generate_plots:
            print("Generating plots...")
            try:
                fig_anc = self.plot_anc()
                analysis_results["plots"].append(str(self.output_dir / "anc_curve.png"))
                fig_neuro = self.plot_neuropathy()
                analysis_results["plots"].append(str(self.output_dir / "neuropathy_curve.png"))
                fig_tumor = self.plot_tumor_size()
                analysis_results["plots"].append(str(self.output_dir / "tumor_size_curve.png"))
                # fig_utility = self.plot_utility() # Add utility plot if desired
                # analysis_results["plots"].append(str(self.output_dir / "utility_curve.png"))
                # fig_cost = self.plot_cost() # Add cost plot if desired
                # analysis_results["plots"].append(str(self.output_dir / "cost_curve.png"))
                print(f"Plots saved to {self.output_dir}")
            except Exception as e:
                print(f"Error generating plots: {e}")
                # import traceback
                # traceback.print_exc()
        
        return analysis_results
