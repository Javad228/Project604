"""
Simplified FOLFOX model for simulating body response.
"""
import numpy as np
from typing import Dict
from params import FOLFOXParams
import math


class FOLFOXModel:
    """Simplified FOLFOX model for simulating body response."""

    def __init__(self, params: FOLFOXParams):
        """Initialize the model with parameters."""
        self.params = params
        self.dt = params.optimization.step_size_days
        self.horizon = params.optimization.horizon_days
        self.T = int(self.horizon / self.dt) # Number of steps

        # Calculate BSA using the Du Bois formula
        weight_kg = params.dosing.patient_weight_kg
        height_cm = params.dosing.patient_height_cm
        if weight_kg <= 0 or height_cm <= 0:
             raise ValueError("Patient weight and height must be positive.")
        self.bsa_m2 = math.sqrt((height_cm * weight_kg) / 3600.0)

        # Pre-calculate dose limits and thresholds in absolute mg using calculated BSA
        self.max_daily_5fu_mg = params.dosing.max_daily_5fu_mg_m2 * self.bsa_m2
        self.max_single_ox_mg = params.dosing.max_single_ox_mg_m2 * self.bsa_m2
        # Calculate absolute chronic neuro threshold using BSA
        self.chronic_neuro_thresh_mg = params.neuropathy.chronic_neuropathy_threshold_mg_m2 * self.bsa_m2 
        self.severe_neutropenia_thresh = params.hematology.severe_neutropenia_threshold

    def get_dosing_schedule(self, num_cycles_to_administer: int) -> (np.ndarray, np.ndarray):
        """Creates a basic, repeating 14-day FOLFOX dosing schedule
           for a specified number of cycles.
           
           Args:
               num_cycles_to_administer: The number of 14-day cycles to apply.

           Returns:
               Tuple[np.ndarray, np.ndarray]: dose_5fu, dose_ox arrays for the horizon
        """
        days = np.arange(self.T) * self.dt
        dose_5fu = np.zeros(self.T)
        dose_ox = np.zeros(self.T)
        
        cycle_len_days = 14
        # Total potential cycles in horizon (not used for looping here)
        # num_cycles = int(np.ceil(self.horizon / cycle_len_days))
        
        # Loop only for the number of cycles to administer
        for cycle in range(num_cycles_to_administer):
            start_day_idx = int(cycle * cycle_len_days / self.dt)
            day1_idx = start_day_idx
            day2_idx = start_day_idx + 1
            
            if day1_idx < self.T:
                # Apply Oxaliplatin only if min days passed (simplistic check)
                if cycle == 0 or self.params.dosing.min_days_between_ox <= cycle_len_days:
                     dose_ox[day1_idx] = self.max_single_ox_mg
                dose_5fu[day1_idx] = self.max_daily_5fu_mg 
            
            if day2_idx < self.T:
                dose_5fu[day2_idx] = self.max_daily_5fu_mg
                
        return dose_5fu, dose_ox

    def simulate(self, num_cycles_to_administer: int) -> Dict[str, np.ndarray]:
        """Runs the simulation step-by-step for a given number of cycles.
        
           Args:
               num_cycles_to_administer: The number of 14-day cycles to apply.

           Returns:
               Dict[str, np.ndarray]: Dictionary containing time-series results.
        """
        
        # Get predefined dosing schedule for the specified number of cycles
        dose_5fu, dose_ox = self.get_dosing_schedule(num_cycles_to_administer)

        
        # Initialize state arrays
        time = np.arange(self.T + 1) * self.dt # T+1 to include final state
        anc = np.zeros(self.T + 1)
        cum_ox = np.zeros(self.T + 1)
        acute_neuropathy = np.zeros(self.T + 1, dtype=int)
        chronic_neuropathy = np.zeros(self.T + 1, dtype=int)
        utility = np.zeros(self.T + 1)
        daily_cost = np.zeros(self.T) # Cost for each day (t=0 to T-1)
        total_cost = np.zeros(self.T + 1) # Cumulative cost
        tumor_size = np.zeros(self.T + 1) # Tumor size over time
        kill_rate = np.zeros(self.T) # Kill rate at each time step
        eff_auc = np.zeros(self.T) # Effective AUC at each time step
        
        # Initial conditions
        anc[0] = self.params.hematology.anc_baseline
        utility[0] = self.params.utility.baseline_utility # Utility at t=0
        cum_ox[0] = 0
        acute_neuropathy[0] = 0
        chronic_neuropathy[0] = 0
        total_cost[0] = 0
        tumor_size[0] = self.params.tumor.initial_size # Initial tumor size
        
        # Simulation loop
        for t in range(self.T):
            # 1. Calculate ANC dynamics (using Euler forward method)
            anc_production = self.params.hematology.k_out * self.params.hematology.anc_baseline
            anc_loss = self.params.hematology.k_out * anc[t]
            toxicity_effect = (self.params.hematology.k_tox_5fu_dose * dose_5fu[t] + 
                               self.params.hematology.k_tox_ox_dose * dose_ox[t]) * anc[t]
            
            d_anc_dt = anc_production - anc_loss - toxicity_effect
            anc[t+1] = max(0, anc[t] + d_anc_dt * self.dt) # Ensure ANC is non-negative

            # 2. Update Cumulative Oxaliplatin
            cum_ox[t+1] = cum_ox[t] + dose_ox[t]

            # 3. Update Neuropathy Status
            # Acute: Occurs if Oxaliplatin was given in this step
            acute_neuropathy[t+1] = 1 if dose_ox[t] > 0 else 0
            
            # Chronic: Occurs if cumulative dose exceeds threshold
            # Use the pre-calculated absolute threshold
            if cum_ox[t+1] >= self.chronic_neuro_thresh_mg:
                chronic_neuropathy[t+1] = 1
            else:
                chronic_neuropathy[t+1] = chronic_neuropathy[t] # Persists if already occurred
            
            # 4. Calculate tumor dynamics using E-max/Hill equation with drug persistence
            # Convert dose to AUC using the simple PK shortcut: AUC ≈ Dose/Clearance
            # Calculate the AUC for each drug
            auc_ox = dose_ox[t] / self.params.tumor.clearance_ox_L_h
            auc_5fu = dose_5fu[t] / self.params.tumor.clearance_5fu_L_h
            
            # Drug persistence: Add residual effect from previous days (simple exponential decay)
            # If this is not the first day, add some persistence from previous effective AUC
            persistence_factor = 0.7  # Drug effect decays by 30% per day
            if t > 0:
                eff_auc[t] = (self.params.tumor.alpha_ox * auc_ox + 
                              self.params.tumor.alpha_5fu * auc_5fu + 
                              eff_auc[t-1] * persistence_factor)
            else:
                eff_auc[t] = self.params.tumor.alpha_ox * auc_ox + self.params.tumor.alpha_5fu * auc_5fu
            
            # Calculate kill rate using the E-max/Hill equation
            # Even if no drug given today, there may be residual effect
            if eff_auc[t] > 0:
                numerator = self.params.tumor.E_max * (eff_auc[t] ** self.params.tumor.hill_coef)
                denominator = (eff_auc[t] ** self.params.tumor.hill_coef) + (self.params.tumor.EC_50 ** self.params.tumor.hill_coef)
                kill_rate[t] = numerator / denominator
            else:
                kill_rate[t] = 0
            
            # Update tumor size (growth - kill)
            growth = self.params.tumor.growth_rate * tumor_size[t]
            kill = kill_rate[t] * tumor_size[t]
            print(f"Step {t}: growth={growth:.4f}, kill={kill:.4f}, kill_rate={kill_rate[t]:.4f}, tumor_size={tumor_size[t]:.4f}")
            tumor_size[t+1] = max(0, tumor_size[t] + (growth - kill) * self.dt) # Ensure non-negative
                
            # 5. Calculate Daily Cost
            cost_today = 0
            # Drug costs
            cost_today += dose_5fu[t] * self.params.economics.cost_5fu_mg
            cost_today += dose_ox[t] * self.params.economics.cost_ox_mg
            # Fee costs
            if dose_5fu[t] > 0 or dose_ox[t] > 0: # Infusion fee if any drug given
                 cost_today += self.params.economics.cost_infusion_day
            if dose_5fu[t] > 0: # Pump fee only if 5FU given
                 cost_today += self.params.economics.cost_pump_day
            daily_cost[t] = cost_today
            total_cost[t+1] = total_cost[t] + cost_today

            # 6. Calculate Utility (now incorporating tumor size penalty)
            # Start with baseline
            current_utility = self.params.utility.baseline_utility
            # Penalty for severe neutropenia
            if anc[t+1] < self.severe_neutropenia_thresh:
                current_utility += self.params.utility.neutropenia_penalty
            # Penalty for any neuropathy (acute OR chronic)
            if acute_neuropathy[t+1] == 1 or chronic_neuropathy[t+1] == 1:
                current_utility += self.params.utility.neuropathy_penalty
            # Penalty for cost incurred today
            current_utility -= daily_cost[t] * self.params.economics.cost_utility_factor
            # Penalty for tumor size (normalized by initial size)
            tumor_penalty = -self.params.tumor.tumor_weight_in_utility * (tumor_size[t+1] / self.params.tumor.initial_size)
            current_utility += tumor_penalty
            
            utility[t+1] = current_utility
            
        # Return results dictionary
        results = {
            "time": time,
            "dose_5fu": np.append(dose_5fu, 0), # Pad dose arrays for length T+1
            "dose_ox": np.append(dose_ox, 0),
            "anc": anc,
            "acute_neuropathy": acute_neuropathy,
            "chronic_neuropathy": chronic_neuropathy,
            "cum_ox": cum_ox,
            "utility": utility,
            "chronic_neuropathy_threshold_mg": np.full(self.T + 1, self.chronic_neuro_thresh_mg),
            "daily_cost": np.append(daily_cost, 0), # Pad cost array for length T+1
            "total_cost": total_cost,
            "tumor_size": tumor_size,
            "kill_rate": np.append(kill_rate, 0), # Pad kill_rate array for length T+1
            "effective_auc": np.append(eff_auc, 0) # Pad effective_auc array for length T+1
        }
        return results

    # Keep solve method for compatibility, pass through the cycle count
    def solve(self, num_cycles_to_administer: int) -> Dict[str, np.ndarray]:
        """Runs the simulation for a specific number of cycles (wrapper for simulate)."""
        return self.simulate(num_cycles_to_administer)
