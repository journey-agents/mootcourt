# Claims audit (convergence plan, Task 3 step 6)

Written 4 November 2026 by the statistician auditor against the run 6 build of `paper/main.pdf` (built 14:43, from `paper/main.tex` and `paper/sections/*.tex` of 14:34) and the register `paper/reviews/claims.md`. Every row's report file was opened and its key resolved by hand with the resolver of `scripts/claims_audit.py`; every other number in the quoted sentence was read from the same tables. The auditor read no file under `paper/reviews/round-00` or `paper/reviews/round-01`.

Reading rules applied, from the rubric's R1 and Section 5 of the paper: a plain by-test interval supports "within the interval" language and a single pooled comparison; an adjusted bound supports a claim read across a table; an interval kind of none supports no comparative claim; the pooled interval is the primary claim and per-cell and per-year intervals are descriptive; a calibration percentile above 95 rejects; the gates are a sizing convention and a powered claim rests on its interval; the learning curve is read against the base rate of the full history at the final origin, as its caption states.

A printed digit that differs from the report leaf by one unit at the printed precision is recorded as weakened with the corrected digit, because the paper writer applies every line and the generated tables already print the leaf's value.

## Rows

C1: supported
C2: supported
C3: supported
C4: supported (the key holds P0 minus P1, minus 0.1493; the sentence prints the magnitude, 0.149; see the convention list below)
C5: supported (80 and 90 percent coverage of 0.812 and 0.895 pooled)
C6: supported
C7: supported (gates.json, base rate 0.09, target 0.90, n_400 is 250; the script cannot read the quoted-key form, see below)
C8: supported
C9: supported (the 90 percent interval; the 80 percent runs 1.00 to 0.53)
C10: supported (0.000447, interval minus 0.0003 to 0.0012)
C11: supported (share admitted 0.972 at 11,100 tests, 7,400 rows per cell against 7,417 in the headline-only cell)
C12: weakened: and the rung recovers about a fifth of it (0.18, 0.16 to 0.20, Section 6.8) (reason: the recovered fraction is 0.180 with a by-test interval of 0.164 to 0.197, which excludes 0.20, so "a fifth" without a qualifier overstates the point and the interval)
C13: supported
C14: weakened: Ranking tests by predicted win probability captures more positive lift than a random order matched on the number of arms for a TF-IDF text classifier (3.9 points, interval 2.2 to 5.4) (reason: diff_matched is 0.03946, which rounds to 3.9 points; the src comment's 0.0395 was rounded a second time; the comparative claim itself is supported, the adjusted bound 0.016 to 0.063 clears zero)
C15: supported (constant_within_cell is true for P1; its matched difference is minus 0.004, minus 0.012 to 0.005)
C16: supported
C17: supported (undecidable at this n in the pooled row and in all four metric cells)
C18: supported (design claim)
C19: supported (design claim)
C20: supported
C21: supported (0.0019 against 0.0015, both intervals spanning zero)
C22: supported
C23: weakened: ablations over weight, bandwidth, features, selection, admission, pooling and prior shape leave it unchanged (no setting of the rung beats the prior; leave-one-test-out selection scores minus 0.861 and a fixed weight of one minus 0.869 against the prior's minus 0.857, Section 7) (reason: the fixed weight of one, which the sentence counts among the ablations over weight, departs from the prior by 0.012 nats, more than leave-one-test-out's 0.004, so leave-one-test-out is not the largest departure)
C24: weakened: a positive control in which the guard admits a planted text signal at the size of the largest cell and the rung recovers about a fifth of it (reason: as C12)
C25: supported
C26: weakened: The six hypotheses, fixed in writing before the final runs and unchanged since (Section 9), are reported as they came out, part by part: one confirmed, four in part and one refuted (reason: the paper states no verdict rule in Section 5 or Section 9; by the rule it applies to the third and fourth hypotheses, where a hypothesis with a holding part and a failing part is held in part, the first hypothesis is held in part too, since the prior beats the base rate at every origin and the rung does not beat the prior on image-only, both as planned, and only the headline-only part fails; the writer may instead keep one, three and two by stating in Section 9 the rule that makes the first hypothesis refuted while the third and fourth are in part)
C27: weakened: H1 read back: the first half holds, P1 above P0 at every origin, by the narrowest margin at January 2015 (minus 0.731 against minus 0.799) (reason: the margins by origin after burn-in are 0.140 nats at July 2013, 0.125 at October 2013, 0.077 at January 2014, 0.120 at April 2014, 0.249 at July 2014, 0.144 at October 2014, 0.068 at January 2015 and 0.077 at April 2015; July 2013 has the lowest pair of scores, not the narrowest margin; the register key should move to origin 2015-01-01)
C28: weakened: H1 read back: the rung does not beat the prior on headline-only (plus 0.0008 nats, minus 0.0007 to 0.0020, with the family held fixed) and, as planned, does not beat it on image-only (plus 0.0000, minus 0.0001 to 0.0001), so the headline-only part fails; the verdict word follows the rule chosen under C26 (reason: the hypothesis is stated per cell, and the pooled plus 0.0004 is not the headline-only cell's number; the image-only part holds)
C29: supported
C30: supported
C31: supported
C32: supported
C33: weakened: H4 read back, held in part: abstention 14 percent, and the novelty trigger, the only one that fires after burn-in, changes what is issued, not measurably how well (reason: the 477 rows the reliability trigger withheld score minus 0.956, minus 1.065 to minus 0.852, against minus 0.854 on the issued rows, and their direction accuracy of 0.516, 0.475 to 0.554, sits below the issued rows' 0.582, outside the interval, so the statement about the triggers in general overreaches; Section 6.5 itself calls those rows worse on both)
C34: weakened: H5 read back against the arm-count-matched random order: confirmed for the text classifier (plus 0.039, adjusted interval above zero) (reason: 0.03946; the adjusted lower bound 0.016 supports the verdict)
C35: supported
C36: supported
C37: supported
C38: supported
C39: supported
C40: supported (share_lambda_zero 1.00 in all four metric cells)
C41: supported
C42: supported
C43: supported (P1 minus 0.8566, P0 minus 1.0059, normal-prior P1 minus 0.9566)
C44: supported
C45: supported
C46: weakened: P1 is above P0 on the logarithmic score at every origin, by the narrowest margin at January 2015 (minus 0.731 against minus 0.799), so the first half of the first hypothesis holds (reason: as C27; the register key should move to origin 2015-01-01 for P1 and P0)
C47: supported
C48: supported
C49: supported (the text classifier's 0.555 is the lowest direction accuracy among the rungs; the two direction baselines are not rungs)
C50: weakened: the recalibrated text classifier is the only rung whose pooled interval lies above zero (0.0003 to 0.0087), and its adjusted bound (minus 0.003 to 0.012) does not (reason: adjusted_hi is 0.01249)
C51: weakened: Within each origin and cell stratum the event AUC is 0.500 for P0, 0.530 (0.512 to 0.547) for P1, 0.548 for P2, 0.538 for the local set and 0.564 (0.547 to 0.582) for the text classifier (reason: auc_event_within is 0.56449)
C52: supported
C53: supported (the eight pairs with a weight above zero are seven headline-only origins and April 2015 in image-only)
C54: supported
C55: supported (the other seven differences are 0.0000 to 0.0027)
C56: supported
C57: supported (scale part minus 0.00259, minus 0.0040 to minus 0.0010)
C58: supported
C59: supported
C60: supported
C61: supported (n_200 is 175 at base rate 0.09, target 0.90)
C62: supported
C63: supported (decidable at skill 0.20 only at the simulated dependence; 2.09 rows per test, correlation 0.399, gates 318 and 454, undecidable at this n)
C64: supported
C65: supported
C66: supported
C67: supported (coverage from 0.829 at decile 3 to 0.943 at decile 10)
C68: supported (mean p_sig 0.0999 to 0.1111, event rate 0.0355 to 0.1200)
C69: supported
C70: supported
C71: weakened: Against it the text classifier captures 0.300 (plus 0.039, 0.022 to 0.054) (reason: 0.03946)
C72: supported
C73: supported
C74: supported
C75: supported
C76: supported
C77: supported
C78: weakened: The text classifier stays the best rung and the prior stays at the baseline at budgets of a tenth and a half (the text classifier plus 0.032 and plus 0.036 over the matched baseline, the oracle at 0.384 and 0.940; Table decision-intervals) (reason: the order of the middle rungs changes with the budget: at a tenth the precedent rung, 0.119, sits above the boosted model, 0.118, and the local set, 0.115; at a half the local set, 0.535, sits above the boosted model, 0.519, and the precedent rung, 0.514; the boosted model's adjusted bound clears zero at a tenth, 0.001, and not at a half, minus 0.007; "the ordering holds" is supported only for the top and the bottom of the table)
C79: supported
C80: weakened: The pooled abstention rate is 14.1 percent, and on the 11,373 issued rows P2 scores minus 0.854 against minus 0.856 on all rows (reason: the rate is 0.14147)
C81: supported (the issued rows' minus 0.854 lies inside minus 0.895 to minus 0.750; the direction accuracy 0.560, 0.528 to 0.590, holds the issued 0.582 inside)
C82: supported
C83: supported
C84: weakened: the significant-positive rate itself falls from 0.117 in 2013 to 0.087 in 2014 and 0.057 in 2015, a shift that P0's trailing base rate lags and that the drift rule, which watches the log score against P0 alone, cannot see (reason: event_rate for 2013 is 0.11746)
C85: supported
C86: supported
C87: supported (weeks 20 April, 27 April, 4 May and 11 May 2015, all in the smallest cell; 11 May 2015 is the replay's last week)
C88: supported
C89: weakened: What the archive does show is that the prior is overconfident there: its Brier skill is minus 0.107 (minus 0.237 to minus 0.002; minus 0.326 to 0.111 adjusted, so the skill alone does not resolve it), its expected calibration error of 0.127 sits at percentile 98.8 of the clustered null (design effect 3.8), past the rejection line, and its coverage is 0.78 and 0.86 (reason: the register reads the sentence on the adjusted bound, which spans zero, and 68 tests sit below the gate; the calibration percentile and the coverage carry the overconfidence reading, the skill does not resolve it)
C90: supported
C91: supported
C92: weakened: On the synthetic archive with no text signal the pooled prior recovers the generator's cell means and spreads within a few tenths, covers 78 and 89 percent, has a Brier skill of 0.002 (minus 0.013 to 0.017) with an ECE at percentile 95.2 of the clustered null, just past the rejection line of 95 (97.8 under the independent null), and the guard holds lambda at zero everywhere (reason: ece_percentile is 95.2 and Section 5 rejects calibration above 95; "at the 95th percentile" hides which side of the line the archive with known truth falls on)
C93: supported
C94: supported (gains minus 0.0002 to 0.0093 nats against standard errors of 0.0006 to 0.0097; the largest is 0.96 standard errors)
C95: supported
C96: supported
C97: supported (0.180, 0.164 to 0.197; 0.099 in the headline-only cell; 0.274 and 0.254 at lifts of 2 and 4 percent)
C98: supported (0.000, 0.000, 0.014 and 0.016 at 300 and 1,000 tests for lifts of 0.5 and 1 percent)
C99: weakened: the text classifier scores at or below the base rate at both sizes (Brier skill minus 0.014, minus 0.027 to 0.001, and minus 0.017, minus 0.022 to minus 0.011, pooled) (reason: the interval at 2,000 tests spans zero; the register's interval kind is none, which supports no comparative claim, so the intervals must be shown)
C100: supported (P2 is the only rung at 11,100 tests with a positive log-score difference, 0.0018, 0.0014 to 0.0023, and a negative Brier difference, minus 0.0001, minus 0.0002 to minus 0.0001)
C101: weakened: The prior gives the next result's distribution (0.149 nats better than the base rate) and, at the release gate, nothing about which test will be significant (reason: the gated Brier skill is 0.001, minus 0.002 to 0.005, but the within-stratum event AUC of P1 is 0.530, 0.512 to 0.547, above chance pooled and at chance only inside the largest cell, 0.502, so the unqualified "nothing" overreaches)
C102: weakened: TF-IDF features of the two headlines give a little about which tests will pay (3.9 points of captured lift over the arm-count-matched random order for a classifier) and, after adjustment, nothing about significance (reason: 0.03946; the recalibrated classifier's pooled skill interval lies above zero, 0.0003 to 0.0087, and only its adjusted bound, minus 0.003 to 0.012, spans zero)
C103: supported
C104: supported
C105: weakened: a team adopting it should expect early abstention, a prior whose level and spread arrive within a few hundred rows, precedents that add nothing measurable on this archive (P2 above P1 on the learning curve from 2,991 history rows, 0.030 against 0.029, with overlapping unpaired intervals; plus 0.0004 nats paired on the full backtest, Sections 6.2 and 7) (reason: the learning curve is scored against the full-history base rate as its caption states and carries no paired P2 minus P1 interval, its P1 and P2 intervals overlap at every fraction, and "before a few thousand" implies a measurable gain after, which the paired comparison of Section 6.2 does not show)
C106: supported (design claim)

## Counts

| status | rows |
|---|---|
| supported | 84 |
| weakened | 22 |
| removed | 0 |

Weakened rows: C12, C14, C23, C24, C26, C27, C28, C33, C34, C46, C50, C51, C71, C78, C80, C84, C89, C92, C99, C101, C102, C105. Of these, nine are a last-digit correction (C14, C34, C50, C51, C71, C80, C84, C102 and the digit in C105's companion sentences), two are a factual correction of which origin carries the narrowest margin (C27, C46), two are the verdict count and its first hypothesis (C26, C28), and the rest are sentences that said more than their interval or table supports (C12, C23, C24, C33, C78, C89, C92, C99, C101, C105).

## Key-path typos and convention mismatches (for the paper writer and the script)

None of these changes a claim's status; each is a mismatch between the register's stated conventions and what `scripts/claims_audit.py` implements, or a key that must move with a corrected sentence.

1. C7 and C61: the register's quoted-key form `by_base_rate["0.09"].by_target["0.90"].n_400` is documented in the register's conventions but the script's step parser reads the bracket as a row selector and fails with "'by_base_rate' is not a table". The values resolve by hand (250 and 175). The script needs the quoted-key form, or the register needs a form the script reads.
2. C4 and C101: the key `tables.aggregate[cell=ALL,rung=P0].logscore_vs_p1` holds minus 0.1493 and the sentence prints the magnitude 0.149; the register's conventions say the audit compares the magnitude there, but the script compares the sign and fails. Either the script learns a magnitude flag or the rows cite the two log scores (P1 minus 0.857 and P0 minus 1.006) as C43 does.
3. C15 and C38 (printed value `true`), C17, C25, C39, C63 (printed value `undecidable at this n`) and C62 (printed value `decidable at skill 0.20 and 0.10`): the register's conventions quote a boolean or verdict string as the file holds it, but the script accepts only numbers and fails each row, C62 included, where the strings are equal. The script needs a string and boolean comparison.
4. C27 and C46: after the correction the key path must become `tables.score_by_origin[rung=P1,origin=2015-01-01T00:00:00+00:00].logscore` with printed value minus 0.731 (C27) and `tables.score_by_origin[rung=P0,origin=2015-01-01T00:00:00+00:00].logscore` with printed value minus 0.799 (C46); the src comment on that sentence, which calls July 2013 the narrowest margin after burn-in at 0.140 nats, is wrong as well.
5. C14, C34, C71, C102: printed value becomes 3.9 points or plus 0.039; C80: 14.1 percent; the src comments that carry 0.0395 and 0.1415 should carry the leaf's 0.03946 and 0.14147 so that the double rounding cannot recur.
6. C28: the key should cite the cell the hypothesis names, `tables.aggregate[cell=headline_only,rung=P2].logscore_vs_p1`, printed value plus 0.0008, interval kind plain.
7. C5, C11, C12, C13, C16 and C27: the sentence column carries a parenthetical (a number and a section reference) that is not in the abstract or in Section 9 as printed; harmless for the audit but the column no longer quotes the paper.

## Claim sentences in the paper that are not in the register

Sections within the register's scope (abstract, introduction, hypotheses, Section 6, closing section):

1. Introduction, second paragraph: "a quarter of the tests chosen by a pairwise classifier capture 4.0 points more positive lift than a random order matched on the number of arms, an interval clear of zero after adjustment" (3.9 points; add as a row beside C14).
2. Introduction, second paragraph: "improves the logarithmic score of the next result by 0.149 nats over the cell base rate", "its Brier skill against the base rate on the significant-positive event is 0.001 with a 90 percent interval from minus 0.002 to 0.005, on 3,797 tests against a release gate of 250", "kernel-weighted precedents on the two headlines, held in the prior's own predictive family, equal the prior on skill" (duplicates of C4, C6, C7 and C21; register them or note the duplicate).
3. Section 6.1: "By decile of the realized standard error the mean effect runs from minus 39 to plus 80 percent and the significant-positive rate from 0.5 to 21 percent" (supported: minus 39.17, 80.29, 0.0045, 0.206 in cautionary_deciles).
4. Section 6.2: "The challengers on the same origins and rows score below the prior raw (Brier skill minus 0.088 for the boosted model, minus 0.008 for the local comparison set, 0.005 for the text classifier) and at the prior once recalibrated on visible rows (0.000, 0.001 and 0.005)". The text classifier's raw skill, 0.005 (minus 0.001 to 0.011), is above the prior's 0.001, not below; the sentence should become "two of the challengers score below the prior raw (Brier skill minus 0.088 for the boosted model and minus 0.008 for the local comparison set), the text classifier a little above it (0.005), and all three sit at the prior once recalibrated on visible rows (0.000, 0.001 and 0.005)".
5. Section 6.2: "Pooled, the AUC for the significant-positive event is 0.547 (0.529 to 0.565) for P0, 0.553 for P1, 0.558 for P2 and 0.582 (0.567 to 0.598) for the recalibrated text classifier, and the Murphy resolution term, read as a ranking (Section 5), orders the rungs the same way". The AUC values are supported; the resolution term does not order the rungs the same way: P0's 0.00050 sits above P1's 0.00027 and P2's 0.00031 (Table discrimination). The clause should become "and the resolution term, read as a ranking, puts the recalibrated text classifier first (0.00064) but P0 (0.00050) above P1 and P2 (0.00027 and 0.00031)".
6. Section 6.2, gates paragraph: "the pooled table's own dependence, 3.5 rows and 0.20, gives 199 and 284, still cleared" and "the interval that came back bounds the prior's skill well below the smaller target" (supported: 3.489, 0.201, 199, 284; upper bound 0.005 against 0.10).
7. Section 6.3: "The ratio spans 0.30 to 2.83" (supported: 0.299 to 2.834).
8. Section 6.5: "The triggers change what is issued, not measurably how well" (the same clause as C33's read-back; apply the same weakening).
9. Section 6.7: "the two challengers that run without text sit at the base rate once recalibrated with decision value spanning zero" (supported: minus 0.009, minus 0.076 to 0.045, and 0.015, minus 0.035 to 0.069; decision value 0.042, minus 0.024 to 0.135, and 0.004, minus 0.066 to 0.093).
10. Section 6.8: "the boosted model beats P1 only in the headline-only cell at 2,000 tests". It does so on the Brier score only (minus 0.0044, minus 0.0078 to minus 0.0005) and sits below P1 on the log score there (minus 0.020); the sentence should say "on the Brier score".
11. Section 6.8: "it does not separate an archive with no precedent signal from one whose signal the rung recovers a fifth of" (about a fifth; as C12).
12. Closing section: "a prior whose level and spread arrive within a few hundred rows" sits inside C105's sentence and is supported by the learning curve (0.023, 0.009 to 0.043, at 605 rows; 0.019, minus 0.002 to 0.048, at 244).

Sections outside the register's stated scope, listed because they repeat a weakened claim:

13. Section 7, learning curve: "P2 tracks P1 to 1,204 rows and sits above it from 2,991 rows on (0.030, 0.032 and 0.035 against 0.029, 0.029 and 0.030)" and "a few thousand before the precedents add anything": the points are unpaired and their intervals overlap at every fraction; "add anything" should not read as measured (as C105).
14. Section 9, the guard paragraph: "a rung that recovers a fifth of a planted one-percent lift at the size of the real cell" (about a fifth; as C12).

## Output of `scripts/claims_audit.py`

Command: `cd /Users/yingjieli/codes/mootcourt && export MOOTCOURT_DATA_ROOT="/Volumes/Crucial X10/mootcourt-data" && .venv/bin/python scripts/claims_audit.py paper/reviews/claims.md paper/data/run6-forward-chaining`, exit status 1.

A first invocation at 15:01 reported "report ... not found in paper/data/run6-forward-chaining" for all 102 rows with a key; the files were present with 13:42 timestamps and a second invocation at 15:03 resolved every path, so the first result is recorded here and not explained. The second invocation printed:

```
    C4: printed 0.149 but the report holds -0.1493
    C7: by_base_rate["0.09"].by_target["0.90"].n_400 does not resolve in paper/data/run6-forward-chaining/gates.json: "'by_base_rate' is not a table"
    C14: printed 4.0 points but the report holds 0.03946
    C15: printed value 'true' holds no number
    C17: printed value 'undecidable at this n' holds no number
    C25: printed value 'undecidable at this n' holds no number
    C34: printed plus 0.040 but the report holds 0.03946
    C38: printed value 'true' holds no number
    C39: printed value 'undecidable at this n' holds no number
    C61: by_base_rate["0.09"].by_target["0.90"].n_200 does not resolve in paper/data/run6-forward-chaining/gates.json: "'by_base_rate' is not a table"
    C62: report holds 'decidable at skill 0.20 and 0.10', not a number, for printed decidable at skill 0.20 and 0.10
    C63: printed value 'undecidable at this n' holds no number
    C71: printed plus 0.040 but the report holds 0.03946
    C80: printed 14.2 percent but the report holds 14.15
    C101: printed 0.149 but the report holds -0.1493
    C102: printed 4.0 points but the report holds 0.03946
```

Of the sixteen rows the script fails, five are value failures that this audit records as weakened (C14, C34, C71, C80, C102) and eleven are convention mismatches listed above (C4, C7, C15, C17, C25, C38, C39, C61, C62, C63, C101).
