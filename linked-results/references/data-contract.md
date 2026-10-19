# The inputs: study.json, data, participants, stats sheet, methods

Paths in `study.json` are relative to its own folder. The example (`example/study.json` with
`data/`) uses every field described here except between-participant factors.

## Contents
1. study.json
2. Data files
3. The stats sheet
4. methods.md and its placeholders
5. What the builder checks

## 1. study.json

```json
{
  "title": "Muscle vibrations: accelerometry and ultrafast ultrasonography",
  "file_name": "Muscle vibration results",
  "subtitle": "… ({n} participants) …",
  "footer": "HTML allowed: the source article, a link to this skill",
  "data": {"dir": "../data", "id_column": 0, "column_pattern": ["Device", "Activation", "Axis"],
           "separator": ".", "participant_prefix": "P"},
  "participants": {"file": "participants.csv", "id": "id"},
  "stats": {"file": "../data/stats.csv", "alpha": 0.05},
  "factors": [ … ],
  "split": { … },
  "outcomes": [ … ],
  "results": [ … ],
  "methods": "methods.md"
}
```

| Field | Meaning |
|---|---|
| `title`, `subtitle`, `footer` | Shown on the page. `{n}` in the subtitle is the number of participants. The footer is HTML (links). |
| `file_name` | The page's name without `.html` (default: the title). |
| `data.column_pattern` | What each part of a column name is, in order. Every within factor and the split must appear; between factors must not (they come from the participants file). |
| `data.separator` | Between the parts of a column name (`.` in `ACC.C.L`). |
| `data.id_column` | The column of participant IDs (0 = first). IDs are sorted in natural order (S2 before S10) and shown as `<participant_prefix>1…n`. |
| `participants` | A CSV with one row per participant (the data's IDs in `id`): the between factors (a column named as the factor's `id`, or its `column`) and the characteristics shown in the methods (below). **Anonymized**: no names, initials, birth dates or original subject numbers. |
| `stats.alpha` | Significance: p ≤ alpha. |
| `correlations` | Optional: the correlations sheet and how its rows map to the data (below). |

### participants: the characteristics
```json
"participants": {"file": "../data/participant_info.csv", "id": "id", "section": "Participants",
  "categorical": [{"id": "sex", "name": "Sex", "levels": [{"code": "M", "name": "man", "plural": "men"},
                                                          {"code": "F", "name": "woman", "plural": "women"}]}],
  "variables": [{"id": "age", "name": "Age", "unit": "years", "dec": 1},
                {"id": "fat_thickness", "name": "Fat thickness", "noun": "the fat thickness", "unit": "mm", "dec": 1}]}
```
- `section`: the `methods.md` section after which the participants' table, figure and values go (the build
  stops if it does not exist).
- `variables`: numeric columns; `dec` is for means and SDs; values recorded as whole numbers show without
  decimals. `noun` is used by the correlation texts.
- `categorical`: coded columns (every code must be listed); counts can be cited (`{count:sex=M}`).
- Hovering a participant anywhere in the document shows these characteristics.

### correlations
```json
"correlations": {"file": "../data/correlations.csv", "x": "fat_thickness",
                 "outcomes": ["peak_acceleration", "main_frequency", "median_frequency", "damping"], "by": "Activation",
                 "strength": [[0.8, "very strong"], [0.6, "strong"]]}
```
- `x`: a variable of the participants file. `by`: the factor whose levels each get a correlation.
- y is defined per row of the sheet (`y` column, §3.4) and computed by the builder from the data.
- `strength`: words for |r| at or above each threshold, used only when the correlation is significant.
- A results tab `{"label": "Correlation with fat thickness", "correlations": true}` shows them.

### factors (one or two)
```json
{"id": "Device", "name": "Device", "noun": "device", "plural": "devices", "within": true, "reference": "Echo",
 "levels": [
   {"code": "Echo", "name": "Ultrasonography", "short": "US", "phrase": "with ultrasonography",
    "color": "#2a78d6", "color_dark": "#3987e5"},
   {"code": "ACC", "name": "Accelerometry", "short": "ACC", "phrase": "with accelerometry",
    "color": "#eb6834", "color_dark": "#d95926"}]}
```
- `code`: as in the column names (within) or the participants file (between), and in the stats sheet.
- `reference`: the level every difference is taken against (test − reference) and the denominator of
  relative differences. For a pair without the reference, the earlier level in `levels` is the reference.
- `noun`, `plural`, `phrase`: the words of the generated texts ("did not differ between **devices**",
  "lower **with accelerometry** than **with ultrasonography**", "The **device** effect depended on the
  **activation level**"). Phrases must read after "was higher": `with …`, `in the … group`, `at pre`.
- The order of `factors` is the order of the readings, the table's columns (second factor outer) and the
  figure's rows.
- Colours: one validated categorical pair per factor, light and dark (the default palette of the
  dataviz guidance passes; check new ones for colour-blind separation).

### split (optional)
Separate analyses for each level of a factor that is not in the ANOVA (an axis, a side, a muscle):
`{"id": "Axis", "name": "Axis", "levels": [{"code": "L", "name": "Lateral", "long": "Lateral (mediolateral) axis"}]}`.
Each outcome × split level is one row of the tables and one analysis in the stats sheet. `long` opens its
paragraph in the texts.

### outcomes
```json
{"id": "Fmain", "file": "Fmain.csv", "name": "Main frequency", "noun": "the main frequency", "unit": "Hz", "dec": 1}
{"id": "EMG", "file": "EMG.csv", "name": "Vastus lateralis activation", "noun": "the activation", "unit": "% of maximal",
 "dec": 1, "split": false, "fixed": {"Axis": "L"}, "relative": false}
```
- `id`: as in the stats sheet's `outcome`. `noun` starts the sentences ("The main frequency was…").
- `dec`: decimals of means, SDs and differences (relative differences: 1; p: 3; g: 2; per-participant
  values: `dec` + 1).
- `split: false` analyses the outcome once; `fixed` then picks the columns (here the EMG, identical on both
  axes, is read from the `L` columns).
- `relative: false` drops relative differences (a reference near 0, a % already).
- A unit starting with `%` is written without a space ("+37.1% of maximal").

### results (the tabs)
```json
[{"label": "Vibrations", "tabs": [{"label": "Main frequency", "outcomes": ["Fmain"]}, …]},
 {"label": "EMG", "tabs": [{"label": "Activation", "outcomes": ["EMG"]}]}]
```
Top level: the chips under Results. Each tab lists its outcomes; a tab with one outcome has one row per
split level, a tab with several outcomes one row per outcome × split level. One group or one tab hides its
chip bar.

## 2. Data files
Wide CSV, UTF-8 (a BOM is fine), one row per participant, the same participants in every file:
```
"","ACC.C.L","Echo.C.L","ACC.R.L","Echo.R.L","ACC.C.V","Echo.C.V","ACC.R.V","Echo.R.V"
"S1",6.70,20.50,12.49,16.33,19.28,41.20,33.22,23.96
```
- One value per participant and condition: the participant's mean over trials.
- Empty, `NA` or `NaN` is missing. A participant missing a value of a row is left out of that row
  (listwise, as the ANOVA does), and the row's n says so.
- Other layouts (long format, one file per condition, Excel): convert to this first, with a short script,
  and keep the conversion with the data.

## 3. The stats sheet
One CSV for the whole study. One row per ANOVA term and one per comparison, for each outcome × split.

| Column | ANOVA row | Comparison row |
|---|---|---|
| `outcome` | outcome id | outcome id |
| `split` | split code, empty when none | same |
| `test` | `ANOVA` | `posthoc` |
| `effect` | the term: `Device`, `Activation`, `Device:Activation` (also `×`, `*`, ` x `) | the family: the main effect (`Device`) or the interaction (`Device:Activation`) |
| `factor` | – | the factor whose levels are compared |
| `at` | – | the fixed levels of the other factor, `Activation=R` (`;` between several) |
| `level_a`, `level_b` | – | the two levels compared (codes) |
| `stat`, `value` | `F` and its value | `t` and its value, for `level_a − level_b` |
| `df1`, `df2` | degrees of freedom | `df1` = df of t |
| `threshold` | critical F (optional) | critical \|t\| (optional) |
| `p` | p of the term | p **corrected within its family** |
| `p_own` | – | the comparison's own p (optional) |
| `g` | – | Hedges' g (optional; sign ignored, taken from the means) |
| `diff` | – | `mean(level_a) − mean(level_b)` (optional, but it lets the build check the sign and levels) |
| `n`, `n_perm` | participants; permutations (optional; one common value fills `{n_perm}`) | same |

### 3.1 What a design needs
- Every ANOVA term: each factor, and their interaction with two factors.
- For a factor with more than two levels: every pair of its main effect.
- With two factors: every pair of each factor at every level of the other (both readings of the
  interaction). Give them even when the interaction is not significant: the page shows them pale.
- A two-level main effect may have no comparison row; its comparison is then the ANOVA term itself and
  g is computed from the data.

### 3.2 Conventions the page relies on
- Significant: `p ≤ alpha`. A comparison of the interaction family counts as inside the interaction only
  when the interaction's own p is significant.
- Means are estimated marginal means (the unweighted mean of the cell means, as type III sums of squares),
  so a main-effect difference matches the software's with unequal groups.
- When the sheet has no `g`: paired comparisons get d_z (mean of the paired differences over their SD),
  independent groups the pooled-SD d, both × the small-sample correction 1 − 3/(4ν − 1). The reading guide
  then says so.

### 3.3 Getting the sheet from common outputs
- **flipANOVAxD / fctSnPM-style 0D tables** (`Tables.aov`, `Tables.posthoc.<A>`, `<A>By<B>`): ANOVA rows
  from `aov` (Effect, F, DF, df2, Fthreshold, pValue); comparisons from each post hoc table (`<A>_1`,
  `<A>_2`, the `<B>` column for `at`, t, nu, threshold, pValue, pOwn, ES, Difference). `Difference` is
  first − second: put it in `diff` unchanged.
- **R** (`afex::aov_ez` + `emmeans::pairs(..., by =)`): `anova_table` for the terms; `pairs()` gives
  `contrast` ("a - b"), `estimate` (= diff), `t.ratio`, `df`, `p.value` for each `by` level.
- **Python** (`pingouin.rm_anova`, `pingouin.pairwise_tests(..., within=[A, B])`): `Source`, `F`, `p-unc` (or
  the corrected column); pairwise `A`, `B`, `T`, `dof`, `p-corr`, `hedges`.
- **JASP / SPSS / jamovi**: export the ANOVA and post hoc tables, then map them as above.

Say in `methods.md` how the p-values were obtained and corrected. The builder takes them as given.

### 3.4 The correlations sheet
One CSV, one row per correlation:

| Column | Meaning |
|---|---|
| `x` | the participants variable (as `correlations.x`) |
| `outcome`, `split` | the outcome and split level (empty when none) |
| `at` | the level of the `by` factor, `Activation=R` |
| `y` | `rel:<factor>=<test>~<ref>`: 100 × (test − ref) / ref per participant; `diff:…`: test − ref |
| `method` | `pearson` (or whatever the analysis used; shown as given) |
| `r` | the correlation; **the build recomputes it from the data and stops if it differs** (participant order, y definition) |
| `p` | p corrected within its family; `p_uncorrected` before the correction |
| `slope`, `intercept` | the least-squares line (computed from the data when missing) |
| `n` | participants |
| `family`, `family_of`, `correction` | the family size, `split` when each split level is its own family (e.g. the 8 tests of each axis), and the method (`holm`) |

Choose the family with the user: correcting over every test at once can remove a result that an article
reported with a per-axis or uncorrected p. Show them the p-values under each choice (§ the example: the
article's median frequency, contracted, is p = 0.074 over 16 tests, 0.051 over its 12, 0.029 per axis).

## 4. methods.md and its placeholders
`## Heading` starts a section; blank lines separate paragraphs. Inline: `**bold**`, `*italic*`,
`<sub>`/`<sup>`, `[text](https://…)`. A `## References` section stays last: the generated "How to read
this document" section goes before it. Placeholders:

| Placeholder | Value |
|---|---|
| `{n}` | participants |
| `{n_perm}` | permutations, when the sheet has one common `n_perm` ("16,384") |
| `{p_min}` | 1/n_perm ("1/16,384 = 0.000061") |
| `{alpha}` | alpha |
| `{n_corr}` | the correlations' family size ("8") |
| `{mean_sd:age}` | mean ± SD of a participants variable ("25.1 ± 4.4"), linked to its table row and panel |
| `{range:age}` | its range ("21–34"), linked |
| `{count:sex=M}` | the count of a categorical level ("12"), linked to those participants' crosses |

An unknown placeholder stops the build.

**Citations.** Each entry of `## References` starts with its key: `[@freedman1983] Freedman D, Lane D (1983).
A nonstochastic … [doi:…](https://doi.org/…)`. In the text, `[@freedman1983]` writes "Freedman & Lane, 1983"
(put your own parentheses around a group: `([@freedman1983]; [@winkler2014])`) and `[@trama2021|n]` writes
"Trama et al. (2021)". The label is built from the entry's "Authors (Year)": one author, two joined by "&",
three or more "et al.". A citation of a key the list does not hold stops the build; an entry never cited is
reported.

## 5. What the builder checks (it stops with a message)
- A column that does not match the pattern, a cell with no column or several, files with different
  participants, duplicate IDs.
- A missing ANOVA term, a missing or extra comparison, an unknown factor or level in the sheet.
- A sheet `diff` that is not the difference of the data's means (swapped levels or sign).
- A correlation whose `r` is not the data's (participants in another order, another y), a missing
  correlation row, an x that the participants file does not hold.
- A participant of the data missing from the participants file; a categorical code that `study.json` does
  not list; a `section` that `methods.md` does not have.
- A text that cites a statistic its row does not hold; an unknown placeholder or citation.
