# Example data

Data of Trama et al. (2021), *IEEE Transactions on Biomedical Engineering*,
[doi:10.1109/TBME.2020.3035838](https://doi.org/10.1109/TBME.2020.3035838): 15 participants, vastus
lateralis vibrations after an impact, measured with a skin-mounted accelerometer and with ultrafast
ultrasonography, with the muscle relaxed and contracted (40% of its maximal activation).

## Outcome files

One row per participant (S1–S15), one column per condition. Each value is the participant's mean over
their retained trials (up to four).

| File | Variable | Unit |
|---|---|---|
| `peak_acceleration.csv` | Peak acceleration of the filtered signal after the impact | m·s⁻² |
| `main_frequency.csv` | Frequency with the most energy | Hz |
| `median_frequency.csv` | Frequency that splits the energy spectrum in two | Hz |
| `damping.csv` | Damping coefficient of the power decay | s⁻¹ |
| `emg.csv` | Mean EMG of the vastus lateralis before the impact (identical on both axes) | % of maximal |

Column names are `<device>.<activation>.<axis>`:
- device: `ACC` accelerometry, `Echo` ultrafast ultrasonography;
- activation: `R` relaxed, `C` contracted;
- axis: `L` lateral (mediolateral), `V` vertical (anteroposterior).

## Participants

`participant_info.csv` (anonymized: the data's IDs only): sex (`M`, `F`), age (years), height (cm), body
mass (kg), subcutaneous fat thickness at the measurement site (mm, skin caliper, mean of three) and maximal
force (N).

## Statistics (computed beforehand; the skill only reads them)

- `stats.csv`: for each outcome and axis (EMG once), a two-way repeated-measures ANOVA (device ×
  activation) with sign-flip permutations of whole participants (Freedman–Lane), every one of the 16,384
  sign patterns: one row per ANOVA term and per comparison (main effects and both readings of the
  interaction), with t, its threshold, p corrected within its family (`p`), p on its own (`p_own`, for
  comparisons only), Hedges' g and the difference `level_a − level_b`.
- `correlations.csv`: for each variable, axis and activation level, Pearson's r between the fat thickness
  and the relative difference 100 × (ACC − Echo) / Echo, with its least-squares slope and intercept; `p` is
  Holm–Bonferroni corrected over the 8 tests of each axis, `p_uncorrected` before it.

Column descriptions: [`../linked-results/references/data-contract.md`](../linked-results/references/data-contract.md) §3.

## License

These data are under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): reuse them freely, citing
Trama et al. (2021), [doi:10.1109/TBME.2020.3035838](https://doi.org/10.1109/TBME.2020.3035838).
