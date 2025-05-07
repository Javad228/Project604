"""
Parameter handling for FOLFOX optimizer.
Loads parameters from YAML configurations and provides dataclass structure.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml


@dataclass
class HematologyParams:
    """Parameters for neutrophil dynamics and toxicity."""
    anc_baseline: float  # Baseline absolute neutrophil count (10^9/L)
    anc_crit: float      # Critical ANC threshold (10^9/L)
    k_out: float         # Neutrophil turnover rate constant
    k_tox_5fu_dose: float = 1e-5  # Toxicity coefficient per mg of 5-FU dose
    k_tox_ox_dose: float = 5e-5   # Toxicity coefficient per mg of Oxaliplatin dose
    severe_neutropenia_threshold: float = 1.0 # ANC threshold for severe neutropenia flag (10^9/L)


@dataclass
class NeuropathyParams:
    """Parameters for oxaliplatin-induced peripheral neuropathy."""
    chronic_neuropathy_threshold_mg_m2: float = 850.0 # Threshold (mg/m2) for chronic neuropathy


@dataclass
class DosingParams:
    """Parameters related to chemotherapy dosing."""
    max_daily_5fu_mg_m2: float  # Max rate for 5FU infusion (mg/m2/day)
    max_single_ox_mg_m2: float  # Max single bolus dose for Oxaliplatin (mg/m2)
    min_days_between_ox: int    # Minimum days between Oxaliplatin doses
    patient_weight_kg: float    # Patient weight in kilograms
    patient_height_cm: float    # Patient height in centimeters


@dataclass
class UtilityParams:
    """Parameters for utility calculations (Simplified Additive Model)."""
    baseline_utility: float = 0.76     # Baseline utility (no side effects)
    neutropenia_penalty: float = -0.2  # Utility penalty for severe neutropenia
    neuropathy_penalty: float = -0.24 # Utility penalty for any neuropathy (acute or chronic)


@dataclass
class SolverParams:
    """Parameters for the optimization solver."""
    tol: float       # Solver tolerance
    max_iter: int    # Maximum solver iterations


@dataclass
class OptimizationParams:
    """Parameters for optimization setup."""
    horizon_days: int = 180 # ~6 months
    step_size_days: float = 1.0 # Simulate day-by-day


@dataclass
class OutputParams:
    """Parameters for output configuration."""
    results_dir: str = "results"
    save_plots: bool = True # Default to generating plots


@dataclass
class TumorParams:
    """Parameters for tumor growth and response to treatment."""
    initial_size: float = 100.0  # Initial tumor size (arbitrary units, e.g., mm^3)
    growth_rate: float = 0.01    # Natural tumor growth rate (per day)
    E_max: float = 0.8           # Maximum possible kill-rate achievable
    EC_50: float = 70.0          # AUC that gives 50% of E_max
    hill_coef: float = 1.2       # Hill coefficient (h) that controls steepness of effect
    clearance_ox_L_h: float = 8.5 # Oxaliplatin clearance (4.7 L/h/m² * BSA = ~8.5 L/h for BSA=1.8)
    clearance_5fu_L_h: float = 4.5 # 5-FU clearance (2.5 L/h/m² * BSA = ~4.5 L/h for BSA=1.8) 
    alpha_ox: float = 0.015      # Potency scaling factor for oxaliplatin
    alpha_5fu: float = 0.005     # Potency scaling factor for 5-FU
    tumor_weight_in_utility: float = 0.1  # Weight of tumor size in utility calculation

@dataclass
class EconomicsParams:
    """Parameters related to treatment costs."""
    cost_5fu_mg: float = 0.00442
    cost_ox_mg: float = 0.10
    cost_infusion_day: float = 250.0 # Applied if any chemo given
    cost_pump_day: float = 12.0     # Applied if 5FU given
    cost_utility_factor: float = 0.001 # Converts $ to utility penalty (tune this)


@dataclass
class FOLFOXParams:
    """Main parameters class for FOLFOX optimization (Simplified)."""
    hematology: HematologyParams
    neuropathy: NeuropathyParams
    dosing: DosingParams
    utility: UtilityParams
    solver: SolverParams
    optimization: OptimizationParams
    outputs: OutputParams
    economics: EconomicsParams
    tumor: TumorParams
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FOLFOXParams:
        """Create parameters from dictionary."""
        # Handle tumor params with defaults if not present in data
        tumor_params = data.get("tumor", {})
        
        return FOLFOXParams(
            hematology=HematologyParams(**data["hematology"]),
            neuropathy=NeuropathyParams(**data["neuropathy"]),
            dosing=DosingParams(**data["dosing"]),
            utility=UtilityParams(**data["utility"]),
            solver=SolverParams(**data["solver"]),
            optimization=OptimizationParams(
                horizon_days=data["optimization"]["horizon_days"],
                step_size_days=data["optimization"]["step_size_days"],
            ),
            outputs=OutputParams(**data["outputs"]),
            economics=EconomicsParams(**data["economics"]),
            tumor=TumorParams(**tumor_params),
        )

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> FOLFOXParams:
        """Load parameters from YAML file."""
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> FOLFOXParams:
        """Load parameters, using default config if none provided."""
        base_path = Path(__file__).parent
        default_config = base_path / "config_default.yml"
        
        if config_path is None:
            return cls.from_yaml(default_config)
        else:
            custom_config = Path(config_path)
            return cls.from_yaml(custom_config)
    
    def update_from_dict(self, updates: Dict[str, Any]) -> None:
        """Update parameters from a dictionary of overrides."""
        for section, params in updates.items():
            if hasattr(self, section):
                section_obj = getattr(self, section)
                for param, value in params.items():
                    if hasattr(section_obj, param):
                        setattr(section_obj, param, value)
