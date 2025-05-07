import numpy as np
from typing import Dict, Tuple
from params import FOLFOXParams
import math

class FOLFOXModel:
    """Simplified FOLFOX model with one-compartment PK and dynamic dosing optimization support."""

    def __init__(self, params: FOLFOXParams):
        """
        Initialize model parameters and derived quantities.
        Converts all time units to days and volume units appropriately.
        """
        self.params = params
        # Time grid
        self.dt = params.optimization.step_size_days  # days
        self.horizon = params.optimization.horizon_days  # days
        self.T = int(self.horizon / self.dt)

        # Validate patient data
        wt = params.dosing.patient_weight_kg
        ht = params.dosing.patient_height_cm
        if wt <= 0 or ht <= 0:
            raise ValueError("Patient weight and height must be positive.")

        # Body Surface Area (Du Bois)
        self.bsa_m2 = math.sqrt((ht * wt) / 3600.0)

        # Absolute dosing limits (mg)
        self.max_5fu = params.dosing.max_daily_5fu_mg_m2 * self.bsa_m2
        self.max_ox = params.dosing.max_single_ox_mg_m2 * self.bsa_m2

        # Neuropathy and neutropenia thresholds
        self.chronic_neuro_thresh = params.neuropathy.chronic_neuropathy_threshold_mg_m2 * self.bsa_m2
        self.anc_thresh = params.hematology.severe_neutropenia_threshold

        # PK parameters: convert clearance from L/h to L/day
        self.cl_5fu = params.tumor.clearance_5fu_L_h * 24.0
        self.cl_ox = params.tumor.clearance_ox_L_h * 24.0
        self.V_5fu = params.tumor.volume_5fu_L
        self.V_ox = params.tumor.volume_ox_L

    def get_dosing_schedule(self, num_cycles: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a 14-day cycle schedule for given number of cycles,
        enforcing minimum spacing for oxaliplatin.
        """
        dose_5fu = np.zeros(self.T)
        dose_ox = np.zeros(self.T)
        cycle_days = 14
        last_ox_idx = -np.inf
        min_spacing_idx = int(self.params.dosing.min_days_between_ox / self.dt)

        for cycle in range(num_cycles):
            day1 = int(cycle * cycle_days / self.dt)
            day2 = day1 + 1

            if day1 < self.T:
                # 5-FU on both day1 and day2
                dose_5fu[day1] = self.max_5fu
                if day2 < self.T:
                    dose_5fu[day2] = self.max_5fu
                # Oxaliplatin only if spacing satisfied
                if day1 - last_ox_idx >= min_spacing_idx:
                    dose_ox[day1] = self.max_ox
                    last_ox_idx = day1
        return dose_5fu, dose_ox

    @staticmethod
    def reward(value: float, scale: float = 1.0) -> float:
        """
        Reward function: higher when |value| is small.
        """
        return 1.0 / (1.0 + scale * abs(value))

    def simulate(self, num_cycles: int) -> Dict[str, np.ndarray]:
        """Run simulation with one-compartment PK and PD dynamics."""
        d5fu, dox = self.get_dosing_schedule(num_cycles)

        # States over time (length T+1)
        time = np.arange(self.T + 1) * self.dt
        C5, Cox = np.zeros(self.T+1), np.zeros(self.T+1)
        anc = np.zeros(self.T+1)
        cum_ox = np.zeros(self.T+1)
        acute_neuro = np.zeros(self.T+1, dtype=int)
        chronic_neuro = np.zeros(self.T+1, dtype=int)
        utility = np.zeros(self.T+1)
        total_cost = np.zeros(self.T+1)
        tumor = np.zeros(self.T+1)

        # Initial conditions
        anc[0] = self.params.hematology.anc_baseline
        tumor[0] = self.params.tumor.initial_size
        utility[0] = self.params.utility.baseline_utility

        # Loop
        for t in range(self.T):
            # 1-compartment PK (Euler)
            C5[t+1] = C5[t] + self.dt * ((d5fu[t] / self.V_5fu) - (self.cl_5fu / self.V_5fu) * C5[t])
            Cox[t+1] = Cox[t] + self.dt * ((dox[t] / self.V_ox) - (self.cl_ox / self.V_ox) * Cox[t])

            # ANC dynamics
            prod = self.params.hematology.k_out * self.params.hematology.anc_baseline
            loss = self.params.hematology.k_out * anc[t]
            tox = (self.params.hematology.k_tox_5fu * C5[t] +
                   self.params.hematology.k_tox_ox * Cox[t]) * anc[t]
            anc[t+1] = max(0, anc[t] + self.dt * (prod - loss - tox))

            # Neuropathy
            cum_ox[t+1] = cum_ox[t] + dox[t]
            acute_neuro[t+1] = int(dox[t] > 0)
            chronic_neuro[t+1] = int(cum_ox[t+1] >= self.chronic_neuro_thresh)

            # Tumor kill (Emax/Hill)
            eff_auc = (self.params.tumor.alpha_5fu * C5[t] +
                       self.params.tumor.alpha_ox * Cox[t])
            Emax, EC50, n = (self.params.tumor.E_max,
                             self.params.tumor.EC_50,
                             self.params.tumor.hill_coef)
            kill = (Emax * eff_auc**n) / (eff_auc**n + EC50**n) if eff_auc>0 else 0
            growth = self.params.tumor.growth_rate * tumor[t]
            tumor[t+1] = max(0, tumor[t] + self.dt*(growth - kill * tumor[t]))

            # Cost
            cost = (d5fu[t] * self.params.economics.cost_5fu_mg +
                    dox[t] * self.params.economics.cost_ox_mg)
            if d5fu[t]>0 or dox[t]>0:
                cost += self.params.economics.cost_infusion_day
            total_cost[t+1] = total_cost[t] + cost

            # Utility
            u = self.params.utility.baseline_utility
            if anc[t+1] < self.anc_thresh:
                u -= abs(self.params.utility.neutropenia_cost)
            if acute_neuro[t+1] or chronic_neuro[t+1]:
                u -= abs(self.params.utility.neuropathy_cost)
            u -= total_cost[t+1] * self.params.utility.cost_penalty
            # reward for small tumor
            u += self.reward(tumor[t], scale=self.params.utility.tumor_scale)
            utility[t+1] = u

        return {
            "time": time,
            "C5fu": C5,
            "Cox": Cox,
            "anc": anc,
            "acute_neuropathy": acute_neuro,
            "chronic_neuropathy": chronic_neuro,
            "cum_ox": cum_ox,
            "tumor_size": tumor,
            "utility": utility,
            "total_cost": total_cost
        }

    def solve(self, num_cycles: int) -> Dict[str, np.ndarray]:
        return self.simulate(num_cycles)


