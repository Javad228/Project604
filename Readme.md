# Optimal FOLFOX Scheduler

> **Find the safest, most effective 6‑month FOLFOX dosing plan with one command.**

---

## 📦 Project Overview

This tool builds and solves a nonlinear optimisation model that chooses daily 5‑fluorouracil (5‑FU) infusion rates and bi‑weekly oxaliplatin doses for a 180‑day FOLFOX course.  The solver balances tumour shrinkage against quality‑adjusted life‑years (QALY) while respecting all clinical safety, neuropathy, and budget constraints.

* **Solver**  [Pyomo ≥ 6.7](https://pyomo.readthedocs.io) + [Ipopt](https://coin-or.github.io/Ipopt/)
* **Model**    1‑compartment PK, logistic tumour growth, simple neutrophil turnover
* **Outputs**  CSV schedule, JSON summary, optional PNG plots

---

## ⚙️ Quick Start

```bash
# 1 – clone & install
python -m venv venv && source venv/bin/activate  # (or Windows: venv\Scripts\activate)
pip install -r requirements.txt                  # Pyomo + other Python packages
conda install -c conda-forge ipopt                # Install Ipopt solver on Windows

# 2 – run with defaults (180 d horizon, 1 d step, 0.7 / 0.3 weights)
python optimise_folfox.py                        # writes results/ by default

# 3 – inspect
cat results/summary.json
open results/anc_curve.png   # tumour, ANC, doses, utility plots
```

### Custom Run Examples

```bash
# weekly grid, larger budget, QALY‑heavy objective
python optimise_folfox.py --step 7 --budget 2500 --weights 0.4 0.6

# load your own PK / toxicity constants
python optimise_folfox.py -c my_patient.yml
```

---

## 🗂 Repository Structure

```
optimise_folfox/
├── optimise_folfox.py   # CLI entry‑point
├── model.py             # Pyomo model builder
├── params.py            # dataclass + YAML loader
├── analyse.py           # plotting & CSV export
├── requirements.txt
├── config_default.yml   # all baseline parameters
└── tests/
    └── test_sanity.py
```

---

## 🔧 Configuration (YAML)

All tunable parameters live in **`config_default.yml`**.  Copy & edit it or pass overrides via CLI flags.

```yaml
pk:
  ke_5fu_h: 2.6
  vd_5fu_L: 18
  ke_ox_d: 0.0408           # ln2 / 17 h → d⁻¹
  vd_ox_L: 440
hematology:
  anc_baseline: 4.5
  anc_crit: 1.0
  k_out: 0.15
  k_tox: 0.05
...
```

Every key is documented inline.

---

## 🏁 Outputs

* **`schedule.csv`**    day‑by‑day doses, concentrations, tumour size, ANC, utility.
* **`summary.json`**    final tumour volume, QALY, cost, cumulative oxaliplatin.
* **PNG plots**         (if `--plot` set)

---

## ✅ Testing

Run quick sanity checks (dose limits, ANC floor, solver feasibility):

```bash
pytest
```

---

## 📚 References

Key clinical inputs derived from:

* de Gramont et al., 2000 –  FOLFOX4 in metastatic CRC
* André et al., 2004 –  MOSAIC adjuvant trial
* Gamelin et al., 2008 –  5‑FU therapeutic drug monitoring
* Aballéa et al., 2007 –  Cost‑effectiveness of adjuvant FOLFOX
  See `docs/sources.bib` for the full list.

---

## 🤝 Contributing

1. Fork → create branch → commit changes with tests.
2. Open a PR; keep code 100% type‑checked (`mypy`) and black‑formatted.

---

## 📄 License

MIT  2025 Javad Baghirov
