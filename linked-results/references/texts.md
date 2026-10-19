# The texts: how they are written from the data, and how to change them

Every results paragraph is written by `Texts` in `build_document.py` from one row's data (an outcome ×
split level). Nothing is typed by hand, so a rebuild after new data rewrites every number and every
wording that depends on significance.

## Contents
1. The format of a cited result
2. The paragraph of a two-factor row
3. One factor, more than two levels
4. Linked spans and keys
5. Changing the wording
6. Interpreting, in the texts and in answers

## 1. The format of a cited result
- A comparison: **absolute difference with its unit, relative difference, p**: "−10.0 Hz, −34.8%,
  p = 0.003". Without a relative difference (`"relative": false`): "+37.1% of maximal, p < 0.001".
- An ANOVA term: "(Device × Activation, p < 0.001)", or "(p = 0.850)" after "no interaction between…".
- p to three decimals, "p < 0.001" below; U+2212 for minus; "+" on positive differences.
- Rounding matches the page's `toFixed` (`fixed()`: the float's exact value, ties away from zero), so a
  number reads the same in a text and in a table.
- Direction: "higher" or "lower", for test − reference.

## 2. The paragraph of a two-factor row (A × B)
**Interaction significant:**
1. "The *A-noun* effect depended on the *B-noun* (A × B, p)."
2. A read within each level of B. With two levels each:
   - both comparisons significant, same direction: "*Outcome* was lower *A-test phrase* than *A-ref
     phrase*, more *B1 phrase* (…) than *B2 phrase* (…)." — ordered by the size of the difference, which is
     what a significant interaction licenses;
   - one significant: "… lower … *B1 phrase* (…), but did not differ *B2 phrase* (…)";
   - opposite directions: both clauses, joined by "and";
   - none: "did not differ between *A-plural* *B1 phrase* (…) or *B2 phrase* (…)".
3. The same for B within each level of A, starting "It …".

**Interaction not significant:** the main effects, then the interaction:
"*Outcome* was lower *test* than *ref* (…) and higher *test* than *ref* (…), with no interaction between the
*A-noun* and the *B-noun* (p)." A non-significant main effect reads "it did not differ between *plural*
(p)". The comparisons of the interaction family are not cited: they are outside the interaction.

The paragraph opens with the split level's `long` name in bold ("**Lateral (mediolateral) axis.**"), or,
in a tab of several outcomes, the outcome and the split level.

## 3. One factor, more than two levels
- Two levels: "*Outcome* was higher *test* than *ref* (…)", or "did not differ between *plural* (p)".
- More: "*Outcome* differed between *plural* (p): higher at post than at pre (…), …" listing the
  significant pairs, then "the other comparison(s) not significant" when some are not.
- Inside an interaction, per level of the other factor: the significant pairs, or "no pair of *plural*
  differed".

## 3b. Correlations (one paragraph per split level)
- Significant ones, grouped by direction: "*The relative difference between accelerometry and
  ultrasonography* decreased with *the fat thickness* for the main frequency in the contracted muscle
  (r = −0.77, strong, −3.44% per mm, p = 0.005), … and damping in the relaxed muscle (…)."
- Then, generated from the rest: "The other 4 correlations were not significant (p ≥ 0.192)", with the
  smallest of their p rounded down so that "≥" stays true.
- None significant: "… did not correlate significantly with the fat thickness for any variable (smallest
  p = 0.544)."
- The strength word ("strong", "very strong") only for a significant r; the slope in the y unit per x unit.
- The paragraph says what was correlated, not why. An interpretation ("the thicker the fat, the more
  accelerometry underestimates…") belongs to the user's discussion; read the sign with them: a negative
  relative difference means lower with the test level.

## 3c. Methods
Numbers about the participants are placeholders (`data-contract.md` §4), linked to the participants' table
and figure: "12 men and 3 women (25.1 ± 4.4 years, 176 ± 6 cm, 70.7 ± 9.8 kg)". Citations are `[@key]`.

## 4. Linked spans and keys
Each cited statistic is `<span class="ref" data-row="<row id>" data-k="<key>">…</span>`:
- `t:<term>` an ANOVA term (`t:Device:Activation`);
- `m:<factor>:<test>~<ref>` a main-effect comparison;
- `x:<factor>@<other>=<level>:<test>~<ref>` a comparison inside the interaction family;
- `cell:<code>` a condition (`cell:Echo|R`), `lv:<factor>=<level>` a level over the other factor;
- `r:<by>=<level>` a correlation (row `c:<outcome>|<split>`);
- `pv:<variable>` a participants characteristic and `pc:<category>=<code>` a categorical level (row
  `participants`).

The page relates a comparison to its term (hovering the interaction marks its comparisons, and a
comparison marks its interaction's p). The build asserts that every cited key exists in its row. Means and
SDs cited in a text must sit inside their statistic's span, or in a span with the same key.

## 5. Changing the wording
- **Level and factor words**: `phrase`, `noun`, `plural` in `study.json`, then rebuild. This covers most
  requests ("in the trained group", "at follow-up").
- **Sentence patterns**: edit `Texts.row_paragraph`, `main_clause` or `reading`, keep every number going
  through `cmp_stat()` or `ref()`, run `--check`, and read every paragraph of every tab: a pattern
  change applies to all rows.
- **A sentence that only one study needs** (an interpretation, a link to the article): add it to
  `methods.md` or to a config text, not to a results paragraph with a number typed in it.
- Claims with "only", "every", "no other", "both" must be generated from all the listed results of the
  paragraph, so that they stay true when the data change.
- Keep the article's style: past tense, prose, the effect first, then its size, then p.

## 6. Interpreting, in the texts and in answers
- A significant interaction says the difference between the levels of A is not the same at every level of
  B. Read it one factor at a time (both readings are in the page) and say which reading a sentence
  belongs to.
- A comparison of the interaction family when the interaction is not significant is outside the
  interaction: it mostly describes a main effect at that level. Never present it as an interaction effect.
- A non-significant comparison is not evidence of no difference, especially in small samples; say "did not
  differ significantly" in answers when the distinction matters.
- Each family of comparisons is corrected on its own (a main effect; the interaction's comparisons), not
  across outcomes or splits. Say so when several outcomes are read together.
- Effect sizes are descriptive.
