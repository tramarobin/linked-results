# linked-results

A skill for [Claude Code](https://claude.com/claude-code) (and a plain Python tool) that turns a study's
data and its statistics into **one interactive HTML document**: methods, results texts, tables, violin and
scatter plots with every participant, and each participant's values, all linked to one another.

**Example: [open it online](https://tramarobin.github.io/linked-results/example/muscle-vibration-results.html)**,
built from the data of Trama et al. (2021) in [`data/`](data). The file itself,
[`example/muscle-vibration-results.html`](example/muscle-vibration-results.html), can also be downloaded and
opened in any browser; it needs no internet connection.

## Why I made it

A study with several outcomes, conditions and analyses quickly produces more results than a paper can
show: dozens of tables, figure folders and spreadsheets. When I share them with collaborators, they have to
find which number goes with which figure and which analysis, and the files drift apart every time the
analysis is re-run.

I wanted one file that a collaborator can open and browse without any software:

- **Everything in one place.** The methods, a written summary of every result, the tables, a figure for
  every analysis, the participants' characteristics and every participant's values, organised in tabs.
- **Every number is traceable.** Hover any statistic in the text and the same result is marked in the
  table and in the figure; hover a figure and its statistics are marked in the text and the tables. Hover a
  participant and follow them across every condition, with their characteristics. Hover a citation and read
  its reference.
- **Nothing typed by hand.** The texts are written from the data at each build, so new participants or a
  re-run analysis update every number, every bold value and every "higher" or "lower" in minutes, with no
  copy-paste errors.
- **Easy to share.** One HTML file (under 0.2 MB here) that opens offline, from an email, a shared drive or
  a website.

## What the document contains

- **Methods** (your text, in Markdown), with the participants' characteristics as a table and a figure,
  hoverable citations, and a generated guide on how to read the document.
- **Results**, in tabs and sub-tabs you choose (here: Vibrations, with one sub-tab per variable and one for
  the correlations with fat thickness, and EMG):
  - a paragraph per analysis, in the style of a results section ("The main frequency was lower with
    accelerometry than with ultrasonography, more in the contracted muscle (−26.9 Hz, −48.9%, p < 0.001)
    than in the relaxed muscle (−10.0 Hz, −34.8%, p = 0.003).");
  - a table of means (SD) and ANOVA p-values, bold only when significant;
  - violin plots with every participant, for the main effects and both readings of the interaction, with
    the comparisons' p-values (comparisons outside a non-significant interaction drawn pale);
  - scatter plots with the least-squares line for correlations, with r, slope and p;
  - the full statistics: ANOVA, conditions, comparisons with absolute and relative differences and
    Hedges' g;
  - each participant's values, downloadable as CSV.
- Light and dark themes, a layout that works from a phone to a wide screen, and figures that can be
  enlarged.

## What it does not do

It **does not compute statistics**. You give it the results of your analysis (from MATLAB, R, Python,
JASP, SPSS...) as tidy CSV files, the *stats sheets*; it computes only descriptive values (means, SDs,
differences) and checks them against the sheets. Designs: one or two factors, within and/or between
participants, any number of levels, with optional separate analyses per axis, side or muscle, and
correlations between a participant characteristic and a difference between conditions.

## Using it

### With Claude Code
Copy the [`linked-results`](linked-results) folder into `~/.claude/skills/` (or into a
project's `.claude/skills/`). Then ask, for example: *"Build a results document from the data and the
stats sheet in data/, with a Methods tab from my article."* The skill tells Claude how to write the study
file, anonymize the participants file, convert the statistics, build the page and check it.

### Without Claude
Python 3.9 or later, standard library only:
```
python linked-results/scripts/build_document.py example/study.json --check   # print the texts
python linked-results/scripts/build_document.py example/study.json           # write the page
python linked-results/scripts/check_document.py example/muscle-vibration-results.html   # test it (Edge or Chrome)
```
The inputs are described in
[`linked-results/references/data-contract.md`](linked-results/references/data-contract.md):
- one CSV per outcome (one row per participant, one column per condition);
- the stats sheet (one row per ANOVA term and per comparison), and optionally a correlations sheet;
- an anonymized participants file (optional);
- `study.json` (factor and level names, units, colours, tabs);
- `methods.md`.

## Repository

| Path | What it is |
|---|---|
| `linked-results/` | The skill: `SKILL.md`, `references/` (inputs, texts, page design, checks), `scripts/` (builder, template, checker) |
| `data/` | The example's data (5 outcomes, 15 participants), its anonymized participants file and its two stats sheets; see [`data/README.md`](data/README.md) |
| `example/` | The example's `study.json`, `methods.md` and the built document |

## The example study

Fifteen participants received impacts on the vastus lateralis, relaxed and contracted. The resulting
muscle vibrations were measured with a skin-mounted accelerometer and with ultrafast ultrasonography, on
the lateral (mediolateral) and vertical (anteroposterior) axes. The document compares the devices for the
peak acceleration, main and median frequencies and damping, relates the devices' relative difference to the
subcutaneous fat thickness, and checks that the muscle activation (EMG) was the same for both devices.

The methods are the article's. The statistics differ slightly:
- a two-way repeated-measures ANOVA with sign-flip permutations (exact p-values from all 16,384 sign
  patterns) on each participant's mean values, where the article fitted linear mixed models to every trial;
- the correlations include the peak acceleration, and are Holm–Bonferroni corrected over the 8 tests of
  each axis. The four correlations of the article's Fig. 5 are significant, with the same r and slopes.

## How to cite

If you use this skill, or share results built with it, please cite it:

> Trama, R. (2026). *linked-results: interactive results documents from data and statistics* (Version 1.0.0) [Computer software]. https://github.com/tramarobin/linked-results

GitHub's **Cite this repository** button (from [`CITATION.cff`](CITATION.cff)) gives the same reference in
APA and BibTeX. In a paper or a shared document, a line such as *"Detailed results are available as an
interactive document built with linked-results (Trama, 2026)"* is enough as an acknowledgement.

For the example data and methods, cite the article:

> Trama, R., Hautier, C. A., Souron, R., Lapole, T., Fouré, A., & Blache, Y. (2021). Is accelerometry an
> effective method to assess muscle vibrations in comparison to ultrafast ultrasonography? *IEEE
> Transactions on Biomedical Engineering*. https://doi.org/10.1109/TBME.2020.3035838

## License

The skill, its documentation and the example document are under the [MIT license](LICENSE). The example
data in `data/` are under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): reuse them freely,
citing Trama et al. (2021).

The skill was developed with Claude Code.
