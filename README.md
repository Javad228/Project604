# Simplified FOLFOX Body Response Simulation

This project simulates the physiological response of a patient to a predefined FOLFOX chemotherapy regimen, focusing on key side effects: Absolute Neutrophil Count (ANC) dynamics, Oxaliplatin-induced neuropathy, and patient utility.

It is a simplified version derived from a previous model that included pharmacokinetics, tumor dynamics, and treatment optimization. This version focuses solely on simulating the body's response over time given a fixed treatment schedule.

## Project Components

-   **`model.py`**: Contains the `FOLFOXModel` class. This class implements the core simulation logic:
    -   Calculates ANC levels based on baseline, production/loss rates, and dose-dependent toxicity effects of 5-FU and Oxaliplatin.
    -   Tracks cumulative Oxaliplatin dose.
    -   Determines acute neuropathy (binary flag triggered by Oxaliplatin dose) and chronic neuropathy (binary flag triggered when cumulative dose exceeds a threshold).
    -   Calculates a simple utility score based on a baseline value minus penalties for severe neutropenia and any neuropathy.
    -   Uses a predefined, repeating 14-day dosing cycle (can be modified within the code).
-   **`params.py`**: Defines the data structures (using Python dataclasses) for all model parameters, including:
    -   `HematologyParams`: ANC baseline, turnover rate, toxicity coefficients, neutropenia threshold.
    -   `NeuropathyParams`: Chronic neuropathy cumulative dose threshold in mg/m^2 (e.g., 850.0 mg/m^2). The absolute threshold in mg used by the simulation is calculated using the patient's BSA.
    -   `DosingParams`: Maximum doses per cycle/day, BSA, minimum days between Oxaliplatin.
    -   `UtilityParams`: Baseline utility, penalties for neutropenia and neuropathy.
    -   `OptimizationParams`: Simulation horizon and time step (name is a remnant).
    -   `FOLFOXParams`: Top-level class holding all parameter groups.
    -   Includes logic to load parameters from a YAML configuration file.
-   **`config_default.yml`**: A YAML file containing the default values for all parameters defined in `params.py`. This serves as the baseline configuration.
-   **`optimise_folfox.py`**: The main script used to run the simulation. Despite its name (a holdover from the optimization version), it now loads parameters, initializes the `FOLFOXModel`, runs the simulation, and triggers the analysis.
-   **`analyse.py`**: Contains functions to process and visualize the simulation results stored in the `output/` directory:
    -   Exports time-series data (ANC, doses, neuropathy flags, utility, etc.) to `results.csv`.
    -   Calculates and saves summary statistics (min ANC, final utility, etc.) to `summary.json`.
    -   Generates plots for ANC, neuropathy flags, and utility over time, saving them as PNG files (`anc_plot.png`, `neuropathy_plot.png`, `utility_plot.png`).

## How to Run

1.  **Prerequisites**: Ensure you have Python installed, along with the necessary libraries (primarily `numpy` and `pyyaml`, potentially `matplotlib` if not already installed):
    ```bash
    pip install numpy pyyaml matplotlib
    ```
2.  **Run Simulation (Default Config)**: Execute the main script from the project's root directory. This will use the default weight and height from `config_default.yml`.
    ```bash
    python optimise_folfox.py
    ```
3.  **Run with Specific Patient Dimensions**: Use the `--weight` and `--height` arguments to override the default values:
    ```bash
    python optimise_folfox.py --weight 80 --height 175
    ```
4.  **Run with Plots**: To automatically generate and save plots after the simulation (using either default or specified dimensions):
    ```bash
    # Using default dimensions
    python optimise_folfox.py --plot 
    # Using specific dimensions
    python optimise_folfox.py --weight 80 --height 175 --plot
    ```
5.  **Custom Configuration File**: To use a different parameter configuration file (which might contain different default weight/height):
    ```bash
    python optimise_folfox.py --config my_custom_config.yml
    # You can combine config file with weight/height overrides:
    python optimise_folfox.py --config my_custom_config.yml --weight 75 --height 180 --plot
    ```

## Configuration

Parameters controlling the simulation can be modified by:

1.  Editing the `config_default.yml` file directly (including default `patient_weight_kg` and `patient_height_cm`).
2.  Creating a new YAML configuration file and passing its path via the `--config` command-line argument.
3.  Overriding the patient weight and height specified in the config file using the `--weight` (in kg) and `--height` (in cm) command-line arguments when running `optimise_folfox.py`.

## Output

After running the simulation, the following outputs will be generated in the `output/` directory (which will be created if it doesn't exist):

-   `results.csv`: A CSV file containing the time-series data for all simulated variables.
-   `summary.json`: A JSON file containing key summary metrics from the simulation.
-   (If run with `--plot`)
    -   `anc_plot.png`: Plot showing ANC over time, including the severe neutropenia threshold.
    -   `neuropathy_plot.png`: Plot showing the acute and chronic neuropathy flags over time, along with the cumulative Oxaliplatin dose and threshold.
    -   `utility_plot.png`: Plot showing the calculated utility score over time.
