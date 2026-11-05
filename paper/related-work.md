# Related work for the Moot Court paper (fetch-verified)

Scope: literature relevant to predicting the outcome of an online controlled experiment before it runs, from a ledger of concluded past experiments, with calibrated abstention and a decision-value evaluation. Every entry below was fetch-verified on 2 November 2026 against the URL given. Where the publisher page blocked the fetch, the record was verified through an open mirror (arXiv, RePEc, Crossref, author or repository page) and the fetched URL is the one listed. Entries marked UNVERIFIED could not be fetched after two attempts and carry no details beyond what is stated.

Entry format: authors. Title. Venue, year. Fetched: URL. Claim: what it establishes that matters here. Relation: how this paper differs or builds on it.

## 1. Empirical Bayes and meta-analysis over many A/B tests

1.1 Eduardo M. Azevedo, Alex Deng, Jose L. Montiel Olea, E. Glen Weyl. Empirical Bayes Estimation of Treatment Effects with Many A/B Tests: An Overview. AEA Papers and Proceedings 109: 43-47, 2019. Fetched: https://www.aeaweb.org/articles?id=10.1257/pandp.20191003
Claim: among thousands of tested features, apparent winners mix true effects with lucky draws, and empirical Bayes over the population of past tests separates them and improves per-experiment estimates.
Relation: this is the foundation for our P1 rung; we fit the prior per cell with partial pooling and use it to forecast a not-yet-run test, rather than to correct the estimate of a completed one.

1.2 Eduardo M. Azevedo, Alex Deng, Jose Luis Montiel Olea, Justin Rao, E. Glen Weyl. A/B Testing with Fat Tails. Journal of Political Economy 128(12), 2020. Fetched: https://ideas.repec.org/a/ucp/jpolec/doi10.1086-710607.html (publisher page returned 403; page range on the RePEc record is garbled and is not reproduced here).
Claim: when the distribution of innovation quality is fat-tailed, testing many ideas with small samples beats a few large high-powered tests, and the prior over effects should be heavy-tailed.
Relation: motivates our heavy-tailed (Student-t) cell prior and our portfolio framing; we add out-of-sample scoring of the prior as a forecast and an abstention rule when the prior is not yet reliable.

1.3 Alex Deng. Objective Bayesian Two Sample Hypothesis Testing for Online Controlled Experiments. WWW 2015 Companion (1st Workshop on Online and Offline Evaluation of Web-based Services), Florence, 2015. Fetched: https://exp-platform.com/objective-bayesian-ab/ and Crossref record for DOI 10.1145/2740908.2743062; proceedings PDF at https://archives.iw3c2.org/www2015/documents/proceedings/companion/p913.pdf
Claim: a Bayesian A/B testing framework whose prior is learned from thousands of historical experiments on a search engine, combining Bayesian and frequentist strengths.
Relation: earliest industrial statement of "learn the prior from past tests"; we do the same on public archives, per cell, and score the resulting forecasts against live outcomes.

1.4 Dominic Coey, Tom Cunningham. Improving Treatment Effect Estimators Through Experiment Splitting. The World Wide Web Conference (WWW), pp. 285-295, 2019. Fetched: https://ai.meta.com/research/publications/improving-treatment-effect-estimators-through-experiment-splitting/ and Crossref record for DOI 10.1145/3308558.3313452
Claim: on 226 News Feed A/B tests, a lasso estimator built on repeated experiment splitting cut mean squared predictive error by 44% versus the unshrunk estimator and 18% versus James-Stein shrinkage, and would improve launch decisions.
Relation: establishes that shrinkage calibrated on a ledger of experiments improves decisions; our shrinkage targets a prediction made before any data from the new test exist, and we report decision value as regret rather than MSE.

1.5 David Goldberg, James E. Johndrow. A Decision Theoretic Approach to A/B Testing. arXiv:1710.03410, 2017. Fetched: https://arxiv.org/abs/1710.03410
Claim: the launch decision is a Bayes decision problem with a loss function, so the significance threshold should fall out of the loss and the prior rather than being fixed at 0.05.
Relation: we adopt the decision-theoretic reading but evaluate it empirically as test-and-roll regret on public archives.

1.6 F. Richard Guo, James McQueen, Thomas S. Richardson. Empirical Bayes for Large-scale Randomized Experiments: a Spectral Approach. arXiv:2002.02564, 2020. Fetched: https://arxiv.org/abs/2002.02564
Claim: estimates the prior distribution of treatment effects from past experiments by spectral (Fourier series) maximum likelihood instead of a parametric mixture.
Relation: a nonparametric alternative to our marginal-likelihood Student-t fit; we keep a parametric prior so that the abstention triggers and the leave-one-test-out weight remain interpretable.

1.7 Alex Deng, Yicheng Li, Jiannan Lu, Vivek Ramamurthy. On Post-Selection Inference in A/B Testing. KDD 2021, pp. 2743-2752 (arXiv:1910.03788). Fetched: https://arxiv.org/abs/1910.03788 and Crossref record for DOI 10.1145/3447548.3467129
Claim: taking only significant results at face value distorts estimates and intervals; corrections that combine supervised learning with empirical Bayes reduce selection bias and restore coverage.
Relation: our ledger admission rules exist to prevent exactly this winner-selection contamination of the prior, which the 2026 overview in 1.9 also names as a cause of calibration failure.

1.8 Yongyi Guo, Dominic Coey, Mikael Konutgan, Wenting Li, Chris Schoener, Matt Goldman. Machine Learning for Variance Reduction in Online Experiments. arXiv:2106.07263, 2021. Fetched: https://arxiv.org/abs/2106.07263
Claim: cross-fitted machine learning predictions of outcomes reduce variance of the treatment effect estimate without doing worse than difference in means.
Relation: a within-experiment precision lever; our work is a between-experiment forecasting lever and is complementary. (No fetchable paper by these authors on effect-size distributions was found; the effect-size distribution work is 1.1, 1.2 and 1.6.)

1.9 Marten Schultzberg, Mattias Franberg. Bayesian Inference Procedures for A/B Testing: An Overview. arXiv:2608.12949, 2026. Fetched: https://arxiv.org/abs/2608.12949
Claim: sorts Bayesian A/B setups into three tiers and argues that an empirical Bayes prior fitted to historical tests is the only path to false discovery control and calibrated shrinkage, but that calibration fails when the historical corpus is winner-selected, pooled across programs, or spans heterogeneous metrics.
Relation: directly motivates our ledger admission rules, per-cell priors, and reliability abstention trigger; we add a scored backtest showing when the prior is or is not yet calibrated.

1.10 Bradley Efron, Carl Morris. Data Analysis Using Stein's Estimator and its Generalizations. Journal of the American Statistical Association 70(350): 311-319, 1975. Fetched: Crossref record https://api.crossref.org/works/10.1080/01621459.1975.10479864 and Semantic Scholar record (abstract not served by either).
Claim: the classical demonstration that shrinking many parallel estimates toward a common prior roughly halves mean squared error in real data.
Relation: the ancestor of every rung above P0; cited as the origin of the pooling idea.

Note on company papers: no fetchable paper from LinkedIn, Booking.com, Airbnb or Spotify specifically on priors learned from past experiments was found in this pass. The Spotify-affiliated items found are 1.9 above and 2.7 to 2.8 below (LLM surrogacy, not learned priors). The Netflix items found are decision-value papers and sit in Section 4 (4.5, 4.6).

## 2. Predicting or forecasting experiment outcomes before or early in the test

2.1 Susan Athey, Raj Chetty, Guido W. Imbens, Hyunseung Kang. The Surrogate Index: Combining Short-Term Proxies to Estimate Long-Term Treatment Effects More Rapidly and Precisely. NBER Working Paper 26463, 2019 (revised 2024). Fetched: https://www.nber.org/papers/w26463
Claim: a composite of short-term outcomes can stand in for a long-term outcome and shrink standard errors; shown on a job training experiment.
Relation: surrogates predict the long-run effect of a test that is already running; we predict the headline outcome before the test starts, from other tests.

2.2 Ramesh Johari, Leo Pekelis, David J. Walsh. Always Valid Inference: Bringing Sequential Analysis to A/B Testing. arXiv:1512.04922, 2015 (v3 2019). Fetched: https://arxiv.org/abs/1512.04922
2.3 Ramesh Johari, Pete Koomen, Leonid Pekelis, David Walsh. Always Valid Inference: Continuous Monitoring of A/B Tests. Operations Research 70(3): 1806-1821, 2022. Fetched: Crossref record https://api.crossref.org/works/10.1287/opre.2021.2135
Claim: p-values and confidence intervals that remain valid under continuous monitoring and optional stopping, deployed on hundreds of thousands of experiments.
Relation: anytime-valid inference shortens a running test; our card is issued at time zero and can only shorten the portfolio by deciding which tests to run at all.

2.4 Steven R. Howard, Aaditya Ramdas, Jon McAuliffe, Jasjeet Sekhon. Time-uniform, nonparametric, nonasymptotic confidence sequences. Annals of Statistics 49(2): 1055-1080, 2021 (arXiv:1810.08240). Fetched: https://arxiv.org/abs/1810.08240
Claim: confidence sequences valid at every time under nonparametric assumptions, applied to treatment effect estimation.
Relation: same boundary as 2.2 and 2.3; we cite it for the early-stopping family and do not compete with it.

2.5 Alex Deng, Jiannan Lu, Shouyuan Chen. Continuous Monitoring of A/B Tests without Pain: Optional Stopping in Bayesian Testing. arXiv:1602.05549, 2016. Fetched: https://arxiv.org/abs/1602.05549
Claim: Bayesian testing with proper stopping rules remains valid under continuous monitoring.
Relation: the Bayesian counterpart of 2.3; it still requires the test to run, which is the step our card tries to make optional for low-value candidates.

2.6 Zikun Ye, Hema Yoganarasimhan, Yufeng Zheng. LOLA: LLM-Assisted Online Learning Algorithm for Content Experiments. Marketing Science 44(5): 995-1016, 2025 (arXiv:2406.02611, 2024). Fetched: https://arxiv.org/abs/2406.02611 and https://ideas.repec.org/a/inm/ormksc/v44y2025i5p995-1016.html
Claim: on 17,681 Upworthy headline tests, prompt-based LLM methods perform poorly and embedding or fine-tuned models are only marginally better than chance at naming the winning headline; pairing the best LLM signal with an upper confidence bound bandit beats A/B testing, pure bandits and pure LLMs when traffic is limited.
Relation: closest prior text-based predictor on our dataset; it uses the signal to allocate traffic during a test, while we issue a scored pre-launch probability with abstention and never reallocate traffic. We must report win-prediction accuracy on comparable Upworthy splits.

2.7 Nathan Clark. Predict, Observe, Retrain: Can a Language Model Learn to Pick A/B Test Winners from Its Own Feedback Loop? NeurIPS 2026 workshop poster (Grounded User Simulation for Model Evaluation and Training). Fetched: https://neurips.cc/virtual/2026/169211
Claim: on 2,599 Upworthy headline tests, a LoRA fine-tuned 3B model retrained each round on revealed outcomes picks winners of decisive tests about 52.8% of the time versus a 25.6% random baseline.
Relation: a feedback-loop winner picker on the same archive; we forecast the outcome distribution of a single test, score it with proper scoring rules and calibration, and report decision value rather than top-1 accuracy. Workshop paper, not a main-track publication.

2.8 Joel Persson, Marten Schultzberg, Sebastian Ankargren. Statistical Foundations of LLM-based A/B Testing: A Surrogacy Framework for Human Causal Inference. arXiv:2606.17165, 2026. Fetched: https://arxiv.org/abs/2606.17165
2.9 Sebastian Ankargren, Joel Persson, Marten Schultzberg. When Can LLMs Replace Humans in A/B Tests? Engineering blog post, 13 August 2026. Fetched: https://engineering.atspotify.com/2026/8/when-can-llms-replace-humans-in-a-b-tests/
Claim: LLM-generated outcomes can identify human treatment effects only after calibration against human data; raw GPT-4o-mini predictions on Upworthy headline tests shrink effects toward zero, and the calibration assumptions cannot be checked for new treatments.
Relation: supports our decision to treat any LLM signal as a stacked second opinion at weight zero until it earns weight out of sample, and to abstain under novelty. 2.9 is a blog post and should be cited as such.

2.10 Ashwini Ashokkumar, Luke Hewitt, Isaias Ghezae, Robb Willer. Large Language Models Can Predict the Results of Social Science Experiments. Nature 656: 115-122, 2026 (preprint 2024). Fetched: https://www.gsb.stanford.edu/faculty-research/publications/large-language-models-can-predict-results-social-science-experiments (publisher page not fetched).
Claim: GPT-4 simulations predicted treatment effects of 70 preregistered survey experiments about as well as pooled human forecasters, but consistently overestimated effect sizes.
Relation: the strongest evidence that model-based forecasts of experiments can be useful yet miscalibrated; our pipeline scores calibration explicitly against a perfect-calibration null.

## 3. Human forecasts of experiment results

3.1 Stefano DellaVigna, Devin Pope. Predicting Experimental Results: Who Knows What? Journal of Political Economy 126(6): 2410-2456, 2018 (NBER WP 22566, 2016). Fetched: https://www.nber.org/papers/w22566
Claim: the average of 208 expert forecasts predicted 15 real-effort treatments well, but academic rank and citations did not improve individual accuracy.
Relation: motivates our frozen human forecast rung (P3) and the rule that it earns weight only through out-of-sample skill, not credentials.

3.2 Stefano DellaVigna, Devin Pope, Eva Vivalt. Predict science to improve science. Science 366(6464): 428-429, 2019. Fetched: Crossref record https://api.crossref.org/works/10.1126/science.aaz1704
Claim: systematic collection of predictions of research findings before results are known has many benefits for science.
Relation: our ledger freezes the human forecast before the result is admitted, which is the practice this piece calls for.

3.3 Katherine L. Milkman and colleagues (a megastudy consortium of about one hundred authors; full list on the publisher page). Megastudies improve the impact of applied behavioural science. Nature 600: 478-483, 2021. Fetched: https://www.nature.com/articles/s41586-021-04128-4 (via cookie redirect) and Crossref record for the author list.
Claim: 54 exercise interventions tested on 61,293 gym members; 45% increased visits, and forecasts by impartial judges (professors, practitioners, survey respondents) failed to predict which worked best.
Relation: a megastudy is a ledger built in one shot; we show that a ledger built over time supports calibrated forecasts for new entries, and we quantify when humans do and do not add skill.

3.4 Ron Kohavi, Alex Deng, Lukas Vermeer. A/B Testing Intuition Busters: Common Misunderstandings in Online Controlled Experiments. KDD 2022, pp. 3168-3177. Fetched: https://exp-platform.com/abtestingintuitionbusters/, Crossref record for DOI 10.1145/3534678.3539160, and author PDF https://airbnb.tech/wp-content/uploads/sites/19/2025/10/ABTestingIntuitionBusters.pdf (text extracted locally).
Claim: Table 2 collects published historical success rates (share of ideas judged true improvements): Microsoft 33%, Bing 15%, Booking.com, Google Ads and Netflix about 10%, Airbnb Search 8%, and uses them as the prior in a false positive risk computation; the authors recommend platforms show the false positive risk or posterior probability next to p-values and that surprising results be replicated.
Relation: the program-level base rate used as a prior is exactly our P0 rung; we make it per cell, score it as a forecast, and build the higher rungs on top of it.

3.5 Ron Kohavi, Alex Deng, Brian Frasca, Toby Walker, Ya Xu, Nils Pohlmann. Online controlled experiments at large scale. KDD 2013, pp. 1168-1176. Fetched: Crossref record https://api.crossref.org/works/10.1145/2487575.2488217 (bibliographic only; the full text did not parse).
Claim: describes running hundreds of concurrent experiments on a search engine; widely cited for the statement that most ideas fail to improve the metrics they target. The specific sentence was not verified from the text in this pass.
Relation: source of the practitioner folklore our P0 rung turns into a measured, cell-specific base rate.

3.6 Ron Kohavi, Roger Longbotham, Dan Sommerfield, Randal M. Henne. Controlled experiments on the web: survey and practical guide. Data Mining and Knowledge Discovery 18(1): 140-181, 2009 (online 2008). Fetched: Crossref record https://api.crossref.org/works/10.1007/s10618-008-0114-1 (bibliographic only).
Claim: practical guide to running web experiments, covering power, sample size and variance reduction; the source cited in 3.4 for the 33% success rate.
Relation: background for the base-rate claim; cite with 3.4.

3.7 Ron Kohavi, Stefan Thomke. The Surprising Power of Online Experiments. Harvard Business Review, September-October 2017. Fetched: https://hbr.org/2017/09/the-surprising-power-of-online-experiments
Claim: popular account of large-scale experimentation; the fetched page contains no win-rate figure, only a single 12% revenue example.
Relation: do not cite this for a win rate; cite 3.4 instead.

## 4. Decision value of experimentation

4.1 Elea McDonnell Feit, Ron Berman. Test & Roll: Profit-Maximizing A/B Tests. Marketing Science, 2019, DOI 10.1287/mksc.2019.1194 (arXiv:1811.00457). Fetched: https://arxiv.org/abs/1811.00457 (publisher page returned 403).
Claim: treats the A/B test as a trade-off between the cost of exposing test users to the worse arm and the cost of rolling out the worse arm, and derives profit-maximizing test sizes far below hypothesis-testing recommendations, using a prior on effects.
Relation: our decision-value metric is test-and-roll regret; we supply the prior from the ledger and ask whether prioritizing by predicted win probability lowers regret.

4.2 Ron Kohavi, Diane Tang, Ya Xu. Trustworthy Online Controlled Experiments: A Practical Guide to A/B Testing. Cambridge University Press, 2020. Fetched: https://experimentguide.com/ (publisher page returned 403).
Claim: the standard practitioner reference on running trustworthy experiments, including Twyman's law and the warning that surprising results are usually wrong.
Relation: our reliability and decision-instability triggers operationalize the book's caution as explicit abstention.

4.3 Ron Berman, Christophe Van den Bulte. False Discovery in A/B Testing. Management Science 68(9): 6762-6782, 2022. Fetched: https://econpapers.repec.org/RePEc:inm:ormnsc:v:68:y:2022:i:9:p:6762-6782 (publisher page returned 403).
Claim: across 4,964 effects from 2,766 website experiments, roughly 18 to 25% of results significant at 5% are null effects, rising to 28 to 37% at 10%.
Relation: a portfolio-level estimate of the null share, which is a program-wide base rate; our per-cell base rate and prior refine it and our backtest scores it.

4.4 Randall Lewis, Justin M. Rao. The Unfavorable Economics of Measuring the Returns to Advertising. Quarterly Journal of Economics 130(4): 1941-1973, 2015. Fetched: https://econpapers.repec.org/RePEc:oup:qjecon:v:130:y:2015:i:4:p:1941-1973 (publisher page did not expose the abstract).
Claim: in 25 large advertising experiments, confidence intervals on return were typically over 100 percentage points wide, and informative tests may need more than 10 million person-weeks.
Relation: when single tests are this underpowered, information from the ledger of past tests becomes the main lever; this is the power problem our precedent-based prior addresses.

4.5 Timothy Sudijono, Simon Ejdemyr, Apoorva Lal, Martin Tingley. Optimizing Returns from Experimentation Programs. arXiv:2412.05508, 2024. Fetched: https://arxiv.org/abs/2412.05508
Claim: when the goal is optimization rather than hypothesis testing, firms should test many more ideas with smaller allocations and relaxed thresholds, building on the A/B testing problem of 1.2 and on empirical Bayes analyses of experiment portfolios.
Relation: shares our portfolio view; it changes how tests are run, while we change which tests are run and show the regret difference.

4.6 Winston Chou, Colin Gray, Nathan Kallus, Aurelien Bibaut, Simon Ejdemyr. Evaluating Decision Rules Across Many Weak Experiments. KDD 2025 (arXiv:2502.08763). Fetched: https://arxiv.org/abs/2502.08763
Claim: evaluates launch decision rules by the cumulative returns they would have produced on 123 historical tests, with a cross-validation estimator that is less biased than the plug-in when signals are weak; a new rule is estimated to raise cumulative returns by about 33%.
Relation: the closest prior decision-value evaluation on a ledger of past experiments. Their rules consume each experiment's own data after it runs; our rule consumes only the ledger before the test runs, and we evaluate pre-launch prioritization with abstention.

4.7 Nicholas Larsen, Jonathan Stallrich, Srijan Sengupta, Alex Deng, Ron Kohavi, Nathaniel Stevens. Statistical Challenges in Online Controlled Experiments: A Review of A/B Testing Methodology. arXiv:2212.11366, 2022 (v5 2023). Fetched: https://arxiv.org/abs/2212.11366
Claim: review of the statistical literature on large-scale A/B testing and open challenges; cites failure rates of 90% or higher in some domains.
Relation: general background; useful as the survey citation for the field.

## 5. Calibration, scoring and abstention

5.1 Tilmann Gneiting, Adrian E. Raftery. Strictly Proper Scoring Rules, Prediction, and Estimation. Journal of the American Statistical Association 102(477): 359-378, 2007. Fetched: Crossref record https://api.crossref.org/works/10.1198/016214506000001437 (publisher page returned 403).
Claim: the reference characterization of strictly proper scoring rules for probabilistic forecasts, covering the logarithmic score, the Brier score and the CRPS.
Relation: our log score, CRPS and Brier are taken from here; we add the base-rate reference forecast and the skill floor.

5.2 Tilmann Gneiting, Fadoua Balabdaoui, Adrian E. Raftery. Probabilistic Forecasts, Calibration and Sharpness. Journal of the Royal Statistical Society Series B 69(2): 243-268, 2007. Fetched: Crossref record https://api.crossref.org/works/10.1111/j.1467-9868.2007.00587.x
Claim: good probabilistic forecasts maximize sharpness subject to calibration; distinguishes probabilistic, exceedance and marginal calibration and gives diagnostic tools (PIT histograms, sharpness diagrams, proper scores).
Relation: our interval coverage and calibration checks follow this paradigm.

5.3 James E. Matheson, Robert L. Winkler. Scoring Rules for Continuous Probability Distributions. Management Science 22(10): 1087-1096, 1976. Fetched: https://econpapers.repec.org/RePEc:inm:ormnsc:v:22:y:1976:i:10:p:1087-1096
Claim: introduces scoring rule families for continuous distributions, the origin of the CRPS.
Relation: cited for CRPS.

5.4 Allan H. Murphy. A New Vector Partition of the Probability Score. Journal of Applied Meteorology 12(4): 595-600, 1973. Fetched: Crossref record https://api.crossref.org/works/10.1175/1520-0450(1973)012%3C0595:ANVPOT%3E2.0.CO;2
Claim: decomposes the Brier score into uncertainty, reliability and resolution.
Relation: the uncertainty term is the irreducible floor we report alongside Brier skill against the base rate.

5.5 Jochen Brocker, Leonard A. Smith. Increasing the reliability of reliability diagrams. Weather and Forecasting 22(3): 651-661, 2007. Fetched: https://researchonline.lse.ac.uk/id/eprint/22217 (publisher page returned 403).
Claim: resampling consistency bars show how far observed bin frequencies can wander if the forecasts are perfectly reliable, so a reliability diagram can be read quantitatively.
Relation: our calibration test against a perfect-calibration null is this idea applied to small experiment ledgers.

5.6 Juozas Vaicenavicius, David Widmann, Carl Andersson, Fredrik Lindsten, Jacob Roll, Thomas Schon. Evaluating model calibration in classification. AISTATS 2019, PMLR 89: 3459-3467. Fetched: https://proceedings.mlr.press/v89/vaicenavicius19a.html
Claim: a probabilistic framework for calibration evaluation that exposes pitfalls of binned estimators such as ECE and proposes better quantification and visualization.
Relation: justifies reporting calibration with a null distribution rather than a raw ECE number.

5.7 C. K. Chow. On optimum recognition error and reject tradeoff. IEEE Transactions on Information Theory 16(1): 41-46, 1970. Fetched: Crossref record https://api.crossref.org/works/10.1109/TIT.1970.1054406 (IEEE page returned no text).
Claim: the optimal reject rule and the general relation between error and reject rates.
Relation: the root of our abstention design; our four triggers are reject rules on support, novelty, reliability and decision instability rather than on posterior probability alone.

5.8 Yonatan Geifman, Ran El-Yaniv. Selective Classification for Deep Neural Networks. arXiv:1705.08500, 2017 (venue not listed on the fetched page). Fetched: https://arxiv.org/abs/1705.08500
Claim: turns a trained classifier into a selective one that meets a user-specified risk with high probability by rejecting uncertain inputs.
Relation: we report coverage and risk on the accepted set in the same spirit, with abstention triggers that are interpretable to an experimenter.

5.9 Vladimir Vovk, Alexander Gammerman, Glenn Shafer. Algorithmic Learning in a Random World. Springer, 2005. Fetched: https://link.springer.com/book/10.1007/b106715 (via cookie redirect).
Claim: introduces conformal prediction, which yields prediction sets with finite-sample validity under exchangeability.
Relation: our interval coverage check is a conformal-style validity check; we do not claim exchangeability across cells, which is why the novelty trigger exists.

5.10 Anastasios N. Angelopoulos, Stephen Bates. A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification. arXiv:2107.07511, 2021 (v6 2022). Fetched: https://arxiv.org/abs/2107.07511
Claim: tutorial on conformal prediction including distribution shift, time series and abstaining models.
Relation: cited for the conformal background and for the abstention connection.

## 6. Prior work on the two datasets

6.1 J. Nathan Matias, Kevin Munger, Marianne Aubin Le Quere, Charles Ebersole. The Upworthy Research Archive, a time series of 32,487 experiments in U.S. media. Scientific Data 8: 195, 2021. Fetched: https://www.nature.com/articles/s41597-021-00934-7 (via cookie redirect).
Claim: records every headline A/B test run between 24 January 2013 and 30 April 2015 (32,487 experiments, 150,817 arms, 538,272,878 assignments), split into exploratory (4,873 tests, 22,666 packages), confirmatory (22,743 tests, 105,551 packages) and hold-out (4,871 tests, 22,600 packages) subsets.
Relation: our Upworthy ledger is exactly the exploratory split; the confirmatory and hold-out splits remain available for preregistered replication.

6.2 Akshina Banerjee, Oleg Urminsky. The Language That Drives Engagement: A Systematic Large-scale Analysis of Headline Experiments. Marketing Science 44(3): 566-592, 2025. Fetched: https://ideas.repec.org/a/inm/ormksc/v44y2025i3p566-592.html (publisher page returned 403).
Claim: maps text features to psychological constructs, validates them with raters, and tests which cues causally raise click-through across thousands of Upworthy experiments; cues matter but published advice often gets the direction wrong.
Relation: establishes that headline text carries causal signal, which is what our P2 text kernel exploits; they explain effects after the fact, we forecast them before launch.

6.3 Claire E. Robertson, Nicolas Prollochs, Kaoru Schwarzenegger, Philip Parnamets, Jay J. Van Bavel, Stefan Feuerriegel. Negativity drives online news consumption. Nature Human Behaviour 7: 812-822, 2023. Fetched: https://www.nature.com/articles/s41562-023-01538-4 and Crossref record for the author list.
Claim: on 22,743 Upworthy experiments (about 105,000 headline variants), each additional negative word raised click-through by about 2.3% and positive words lowered it.
Relation: a single strong text feature on our data; our kernel uses the whole text and structured context, and we report whether such features survive out of sample at the level of a single test.

6.4 C. H. Bryan Liu, Angelo Cardoso, Paul Couturier, Emma J. McCoy. Datasets for Online Controlled Experiments. NeurIPS 2021 Track on Datasets and Benchmarks (arXiv:2111.10198). Fetched: https://arxiv.org/abs/2111.10198
Claim: surveys public experiment datasets and releases daily checkpoints of decision metrics from real experiments on a global e-commerce platform (78 experiments with two to five variants and four metrics, per the paper's PDF; the abstract page does not state the count), intended for adaptive stopping research.
Relation: our second ledger; prior uses of it are sequential testing and bandits, not pre-launch outcome prediction.

6.5 Matteo Ottaviani, Stefan M. Herzog, Pietro Leonardo Nickl, Philipp Lorenz-Spreen. How A/B testing changes the dynamics of information spreading on a social network. arXiv:2405.01165, 2024. Fetched: https://arxiv.org/abs/2405.01165
Claim: uses the Upworthy archive as a case study in an agent-based model showing that headline A/B testing alters information spread across network structures.
Relation: a downstream-effects paper on our data; unrelated to forecasting, cited for completeness of archive uses.

6.6 C. H. Bryan Liu. Some Statistical and Data Challenges When Building Early-Stage Digital Experimentation and Measurement Capabilities. PhD thesis, arXiv:2405.03579, 2024. Fetched: https://arxiv.org/abs/2405.03579
Claim: develops methods for organizations building experimentation capability, including the adaptive-stopping use of the dataset in 6.4.
Relation: companion to 6.4; same boundary.

6.7 Ethan Che, Daniel R. Jiang, Hongseok Namkoong, Jimmy Wang. Optimization-Driven Adaptive Experimentation. arXiv:2408.04570, 2024. Fetched: https://arxiv.org/abs/2408.04570
Claim: a mathematical programming framework for short-horizon adaptive experiments. Search results report it builds a simulation from the 78 ASOS experiments; the abstract page does not mention the dataset, so that use is flagged as not confirmed from the fetched page.
Relation: adaptive allocation within a test, not prediction before it.

6.8 Sulgi Kim. Odds-Ratio Thompson Sampling: A Specification and Design Guide for Contrast-Based Multi-Armed Bandits. arXiv:2609.19709, 2026. Fetched: https://arxiv.org/abs/2609.19709
Claim: a bandit that tracks log-odds contrasts and re-estimates the baseline each batch, evaluated on public A/B tests. Use of the ASOS checkpoints is reported by search results but not confirmed from the fetched abstract page.
Relation: same boundary as 6.7.

Also on Upworthy: 2.6 (LOLA), 2.7 (feedback-loop winner picker), 2.9 (LLM surrogate blog post). No 2022 to 2026 paper was found that forecasts a single experiment's outcome distribution before launch on either dataset and scores it against the live result.

## 7. Transfer across experiments and kernel or retrieval-based estimators

7.1 Xinran Li. Learning Across Experiments and Time: Tackling Heterogeneity in A/B Testing. arXiv:2511.21282, 2025. Fetched: https://arxiv.org/abs/2511.21282
Claim: classical empirical Bayes assumes one shared effect distribution; a local empirical Bayes method borrows strength only from a tailored comparison set that is time-aware within an experiment and context-aware across experiments, with strictly lower MSE under heterogeneity.
Relation: the closest prior art to our P2 rung. Differences: our comparison set is kernel-weighted on text and structured features, shrinks toward the P1 cell prior, carries a leave-one-test-out mixing weight, and feeds abstention triggers; and we forecast before launch rather than stabilize a running estimate. Whether it uses the ASOS data is not confirmed from the abstract page.

7.2 Evan T. R. Rosenman, Guillaume Basse, Art B. Owen, Mike Baiocchi. Combining Observational and Experimental Datasets Using Shrinkage Estimators. arXiv:2002.06708, 2020; journal version reported as Biometrics 79(4): 2961-2973, 2023 (journal page not fetched). Fetched: https://arxiv.org/abs/2002.06708
Claim: Stein-type shrinkage that combines an experimental estimate with an auxiliary estimate from another source, with finite-sample conditions for lower risk and a link to sensitivity analysis.
Relation: our precedent estimate plays the role of the auxiliary source and the ledger-fitted prior sets the shrinkage; we evaluate as a forecast rather than as an estimator of a completed trial.

7.3 R. H. Baayen, D. J. Davidson, D. M. Bates. Mixed-effects modeling with crossed random effects for subjects and items. Journal of Memory and Language 59(4): 390-412, 2008. Fetched: Crossref record https://api.crossref.org/works/10.1016/j.jml.2007.12.005 (publisher page returned 403).
Claim: the standard treatment of crossed random effects, where two grouping factors (here, experiment cell and time period, or content and variant) vary independently.
Relation: our per-cell partial pooling is a one-factor hierarchical model; crossed effects are the natural extension and we name them as future work.

7.4 Rebecca DerSimonian, Nan Laird. Meta-analysis in clinical trials. Controlled Clinical Trials 7(3): 177-188, 1986. Fetched: Crossref record https://api.crossref.org/works/10.1016/0197-2456(86)90046-2
Claim: the random-effects meta-analysis estimator that pools heterogeneous trial effects with a between-trial variance.
Relation: P1 is a random-effects meta-analysis of the cell's past tests used as a predictive distribution for the next one.

7.5 Andrew Gelman, Jennifer Hill. Data Analysis Using Regression and Multilevel/Hierarchical Models. Cambridge University Press, 2006/2007. Fetched: Crossref record https://api.crossref.org/works/10.1017/CBO9780511790942
Claim: textbook treatment of multilevel models and partial pooling.
Relation: cited for partial pooling terminology.

No fetchable paper was found that applies kernel-weighted or nearest-neighbour pooling of past experiments on text plus structured features to forecast a new experiment; the nearest is 7.1 (comparison sets) and 2.6 (embedding similarity used for allocation).

## 8. Added in paper pass 3 (3 November 2026): the fetch-verified survey items

Source: `.claude/fleet/muse-survey-verified.md`, where every item was opened on 3 November 2026 at the URL given; the four items the survey marked partly verified (8.5, 8.6, 8.7, 8.10) were opened again on 3 November 2026 for this pass and their identifiers resolve to the works described (8.5: title and the author line as shown, submitted 2 July 2026; 8.6: comment field "Accepted as a workshop paper" at the Workshop on Agent Behavior, v1 3 August 2026; 8.7: title and the six authors as shown, submitted 13 March 2026; 8.10: the Crossref record gives the journal, volume 16, issue 4, pages 437 to 450, 2000; its abstract is not served by any open record, so no specific comparison is attributed to it).

8.1 Kevin Lee, Benjamin Letham, Zhiyuan Jerry Lin, Elodie Samson, Eric Onofrey, Poppy Zhang, Shawndra Hill, Eytan Bakshy. Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing. arXiv:2607.23696, 2026. Fetched: https://arxiv.org/abs/2607.23696 (verified).
Claim: an archive-trained ranker chooses which generated ad creatives enter a 50-arm live test; offline it recovers most of the above-mean creatives in its top 30, and in the live test its top pick finished 43rd, so the authors steer the slate rather than pick the winner.
Relation: the nearest industrial instance of selecting experiments from pre-launch information; it reports offline recall and one live rank, not a calibrated outcome distribution, an abstention rule or proper scores against live results on a public archive. First of the three screening systems R5 asked us to cite.

8.2 Han Li and nineteen co-authors. SimGym: A Framework for A/B Test Simulation in E-Commerce with Traffic-Grounded VLM Agents. arXiv:2605.19219, 2026. Fetched: https://arxiv.org/abs/2605.19219 (verified).
Claim: vision-language agents grounded in production clickstream simulate storefront tests and reach 77 percent directional agreement with observed add-to-cart shifts on 50 live tests.
Relation: screening by simulation rather than precedent; direction only, no abstention, no scored probability. Second of the three screening systems.

8.3 Samuele Mazzanti. How Yelp Built a Back-Testing Engine for Safer, Smarter Ad Budget Allocation. Engineering blog post, 2 February 2026. Fetched: https://engineeringblog.yelp.com/2026/02/how-yelp-built-a-back-testing-engine-for-safer-smarter-ad-budget-allocation.html (verified).
Claim: a back-testing engine replays historical campaign data through the production budgeting code with learned outcome models to preview allocation changes, keeping the live test for final validation.
Relation: archive replay for one algorithm family; never scores a forecast of a product experiment. Third of the three screening systems; cited as a blog post.

8.4 Zhengmian Hu, Lei Shi, Ritwik Sinha, Justin Grover, David Arbour. Experimentation Accelerator: Interpretable Insights and Creative Recommendations for A/B Testing with Content-Aware Ranking. arXiv:2602.13852, 2026. Fetched: https://arxiv.org/abs/2602.13852 (verified).
Claim: a deployed content-aware ranking model trained on historical experiment outcomes prioritizes which variants to test and flags under-expressed attributes.
Relation: evaluated by offline ranking quality on customer experiments, not by calibrated pre-launch probabilities scored against live outcomes.

8.5 T. Dooskin and Squoosh Technical Staff. The Judge Knows When It Knows: Calibrated Abstention for LLM-Based A/B-Test Prediction. arXiv:2608.07517, 2026. Fetched: https://arxiv.org/abs/2608.07517 (partly verified by the survey: the spelling Dooskin and kappa 0.14 in the abstract; re-fetched for this pass).
Claim: a multimodal judge predicting winners from screenshots reaches a kappa of 0.14 on 330 real tests; a vote-margin gate that abstains on about half of them lifts agreement to 0.31.
Relation: direct evidence that abstention, not a better prompt, is the operating point for pre-launch prediction; our four triggers extend the gate from vote margin to support, novelty, reliability and decision instability.

8.6 Stefan Hut, Lorenzo Masoero. Can AI Agents Simulate A/B Test Outcomes? A Validation Framework for Agentic Experimentation. Workshop paper, Workshop on Agent Behavior (co-located with COLM 2026); arXiv:2608.02345. Fetched: https://arxiv.org/abs/2608.02345 (partly verified by the survey: workshop paper, not proceedings; re-fetched for this pass).
Claim: on 67 historical marketing tests a validation framework separates agent error from subsampling error; calibration on a pre-period of realized outcomes cuts squared error about 77-fold.
Relation: validates a simulator against an archive, where we validate a precedent prior; we add abstention and proper scoring.

8.7 Richard Mudd, Abbas Zaidi, Rina Friedberg, Ilya Gorbachev, Anchal Choubey, Houssam Nassif. Breaking the Winner's Curse with Bayesian Hybrid Shrinkage. arXiv:2603.12867, 2026. Fetched: https://arxiv.org/abs/2603.12867 (partly verified by the survey: 167 experiments, production not claimed; re-fetched for this pass).
Claim: a global prior fit from past experiments and an experiment-specific local shrinkage factor correct the winner's curse, evaluated on 167 experiments at a large platform.
Relation: like the rest of Section 1 it corrects the estimate of a completed test; our P1 prior is scored as a forecast of a test that has not run.

8.8 Marten Schultzberg. When Can You Ship on Evals Alone? Trial-Level Surrogacy for Offline Evaluation of LLM Systems. arXiv:2610.10142, 2026. Fetched: https://arxiv.org/abs/2610.10142 (verified).
Claim: trial-level surrogacy yields a closed-form ship, test or kill rule from historical launch logs; on 183 Upworthy interventions the gate sends every intervention to a live test.
Relation: the decidability bar a pre-launch gate must clear on our own archive; our abstention triggers and gates are the analogue for a precedent prior.

8.9 Vickie Zhang, Michael Zhao, Maria Dimakopoulou, Anh Le, Nathan Kallus. Evaluating the Surrogate Index as a Decision-Making Tool Using 200 A/B Tests at Netflix. arXiv:2311.11922, 2023. Fetched: https://arxiv.org/abs/2311.11922 (verified).
Claim: on 200 tests with 1,098 arms, decisions from a 14-day surrogate index agree with 63-day decisions about 95 percent of the time.
Relation: a worked calibration of an early-signal decision rule against realized outcomes, the protocol we apply at time zero rather than at day 14.

8.10 Leonard J. Tashman. Out-of-sample tests of forecasting accuracy: an analysis and review. International Journal of Forecasting 16(4): 437-450, 2000. Fetched: https://api.crossref.org/works/10.1016/S0169-2070(00)00065-0 and https://ideas.repec.org/a/eee/intfor/v16y2000i4p437-450.html (bibliographic record verified; abstract not served).
Claim: the forecasting literature's treatment of out-of-sample accuracy tests, including evaluation from a rolling origin.
Relation: cited for the rolling-origin protocol by name, the credit R5 asked for; no specific comparison is attributed to it because its text could not be fetched.

8.11 James Bisbee, Joshua D. Clinton, Cassy Dorff, Brenton Kenkel, Jennifer M. Larson. Synthetic Replacements for Human Survey Data? The Perils of Large Language Models. Political Analysis 32(4): 401-416, 2024. Fetched: https://api.crossref.org/works/10.1017/pan.2024.5 (verified; publisher page returned 403).
Claim: persona-prompted language models reproduce survey averages with less variance, different regression coefficients, prompt sensitivity and drift over months.
Relation: the failure modes a synthetic-respondent rung must rule out before it earns weight, which is why the stacked second opinion starts at weight zero.

8.12 Joon Sung Park and ten co-authors. LLM Agents Grounded in Self-Reports Enable General-Purpose Simulation of Individuals. arXiv:2411.10109, v1 2024, v3 2026. Fetched: https://arxiv.org/abs/2411.10109 (verified).
Claim: agents built from two-hour interviews with 1,052 people reproduce held-out survey and experimental responses at 83 to 86 percent of participants' own test-retest consistency.
Relation: respondent grounding buys a simulator measurable fidelity on self-report, not on a live product experiment.

8.13 Aliasgar Khimani. Fine-tuning OpenJev on 62,695 A/B Tests. Technical write-up and model release, 23 September 2026 (corrections 24 September 2026). Fetched: https://khimani.dev/blog/fine-tuning-openjev-on-62695-ab-tests/ (partly verified by the survey: the 62,695 are Upworthy arms, not tests; the byline is a handle the site root resolves to the author).
Claim: a fine-tuned text ranker orders held-out Upworthy headline pairs with 0.689 accuracy (0.843 on pairs from significant tests) and falls to 0.522 out of domain.
Relation: a third text-only winner ranker on our archive, scored by pairwise accuracy; it belongs beside 2.6 and 2.7 as a comparator on matched splits.

Credit lines R5 asked for were open at the end of pass 3 and are closed in Section 9 below (added in pass 4, each fetch-verified on 3 November 2026 before it entered the bibliography).

## UNVERIFIED items (not fetchable after two attempts; no details claimed)

U.1 A refinement of the Microsoft empirical Bayes prior attributed to "Deng et al. (2018)" by search summaries of 1.9. Not located. UNVERIFIED.
U.2 A 2024 hierarchical Bayesian paper on cumulative returns to experimentation cited as [ETSB24] in 4.5. Title and venue not located. UNVERIFIED.
U.3 Ron Kohavi, Roger Longbotham. Online Controlled Experiments and A/B Testing. Encyclopedia of Machine Learning and Data Mining. Often quoted for Bing success rates of 10 to 20%; the entry itself was not fetched. UNVERIFIED. Use 3.4 instead.

## Novelty check

Clearly prior art that the paper must cite as such:
- Learning a prior over effects from a corpus of past A/B tests and shrinking toward it: 1.3, 1.1, 1.2, 1.6, 1.4, 1.10, with failure modes named in 1.9 and 1.7. Our P1 rung is an instance of this family and must be presented as such.
- Using the program's historical success rate as the prior for a go/no-go judgment: 3.4 (Table 2 and the recommendation to show a posterior next to the p-value). Our P0 rung is this idea made cell-specific and scored.
- Pooling only from comparable past experiments (local empirical Bayes): 7.1. Our P2 rung must be positioned relative to it.
- Decision-theoretic and test-and-roll framing of the launch decision and the experiment portfolio: 1.5, 4.1, 1.2, 4.5.
- Evaluating decision rules on a ledger of historical experiments by the returns they would have produced: 4.6.
- Text or LLM-based prediction of Upworthy headline winners and its weak accuracy: 2.6, 2.7, 2.9, 2.8.
- Human forecasts of experimental results and their limits: 3.1, 3.2, 3.3, 2.10.
- Scoring, decomposition, consistency bars, selective prediction and conformal validity: 5.1 to 5.10.
- The two datasets and their documented splits: 6.1, 6.4.

## 9. Added in paper pass 4 (3 November 2026): the credit-line references

Fetch-verified in citations round 01 (`.claude/fleet/citations-round01.md`): every record was opened with WebFetch at the URLs listed there (Crossref, OpenAlex, RePEc, Europe PMC, the arXiv API, the Oxford University Press and PLOS landing pages; the ACM, Taylor and Francis and Wiley landing pages returned 403 and were replaced by the open records). Seven verified, one partly (the KDD 2011 conference version of 9.1 rests on the Crossref record alone; the journal version is verified). Where each is cited in `paper/sections/related-work.tex`:

9.1 Shachar Kaufman, Saharon Rosset, Claudia Perlich and Ori Stitelman. Leakage in Data Mining: Formulation, Detection, and Avoidance. ACM Transactions on Knowledge Discovery from Data 6(4): 1 to 21, 2012. DOI 10.1145/2382577.2382579 (conference version KDD 2011, pages 556 to 563, DOI 10.1145/2020408.2020496, three authors). Cited for the word leakage as a named failure of evaluation design, the frame of the cautionary run and the audit (paragraph on scoring and the protocol).

9.2 Francis X. Diebold and Roberto S. Mariano. Comparing Predictive Accuracy. Journal of Business and Economic Statistics 13(3): 253 to 263, 1995. DOI 10.1080/07350015.1995.10524599. Cited with 9.3 for the paired comparison of predictive accuracy that the admission guard and the guarded-against-unguarded comparison are instances of.

9.3 Raffaella Giacomini and Halbert White. Tests of Conditional Predictive Ability. Econometrica 74(6): 1545 to 1578, 2006. DOI 10.1111/j.1468-0262.2006.00718.x. Cited with 9.2.

9.4 Alex Deng, Ulf Knoblich and Jiannan Lu. Applying the Delta Method in Metric Analytics: A Practical Guide with Novel Ideas. KDD 2018, pages 233 to 242. DOI 10.1145/3219819.3219919; arXiv 1803.06336. Cited for the in-test treatment of ratio metrics by the delta method, against which the cautionary run's pre-launch coupling is stated (first paragraph).

9.5 Minyong R. Lee and Milan Shen. Winner's Curse: Bias Estimation for Total Effects of Features in Online Controlled Experiments. KDD 2018, pages 491 to 499. DOI 10.1145/3219819.3219905. Cited for the inflation of the oracle's value, the best positive observed lift among a test's arms (paragraph on decision value).

9.6 Anthony O'Hagan, John W. Stevens and Michael J. Campbell. Assurance in Clinical Trial Design. Pharmaceutical Statistics 4(3): 187 to 201, 2005. DOI 10.1002/pst.175. Cited for the sense in which the card's significance probability is an assurance, a success probability averaged over a prior rather than a power at one assumed effect (paragraph on decision value).

9.7 Sholom Wacholder, Stephen Chanock, Montserrat Garcia-Closas, Laure El Ghormli and Nathaniel Rothman. Assessing the Probability That a Positive Report is False: An Approach for Molecular Epidemiology Studies. Journal of the National Cancer Institute 96(6): 434 to 442, 2004. DOI 10.1093/jnci/djh075. Cited with 9.8 for the lineage of the base-rate-in-a-false-positive-risk computation that the success-rate prior descends from (paragraph on human forecasts and win rates).

9.8 John P. A. Ioannidis. Why Most Published Research Findings Are False. PLoS Medicine 2(8): e124, 2005. DOI 10.1371/journal.pmed.0020124. Cited with 9.7.

Summary count after pass 4: 79 references in `paper/references.bib` (70 from Sections 1 to 8 plus the nine entries above, the KDD 2011 version counted).

Pass 7 (4 November 2026, round 01): `kohavi2017surprising` (3.7) and `kaufman2011leakage` (the KDD 2011 version noted under 9.1) were removed from `paper/references.bib` as uncited; 77 entries remain, each cited at least once in the paper.

Pass 7 part 2a (4 November 2026): `mootcourt2026plan` added, the registered copy of the analysis plan (repository journey-agents/mootcourt-plan, tag plan-registered-2026-11-04, commit f0b088c794dcea1a1eac9872cd15aeb1c2412976, pushed 2026-11-04T17:19:12Z, plan.md sha256 e6dab9062fd1dc59734e5e4374ba429d3edc06efe681f68bb81424d88f45b613, byte-identical to paper/plan.md of commit 145eaf7); 78 entries, cited in Sections 5, 9 and 10.

What appears not to exist in the verified literature (narrowed on 3 November 2026 after the survey of Section 8):
- A pre-launch forecast card for a single proposed experiment that outputs a full outcome distribution and a win probability, abstains under four named triggers (support, novelty, reliability, decision instability), and is scored against the live result on public archives with log score, CRPS, Brier skill against the base rate with its irreducible floor, calibration against a perfect-calibration null, and interval coverage. Prior work either corrects estimates after the test (1.1 to 1.7, 7.1, 8.7), allocates traffic during the test (2.6, 6.7, 6.8), forecasts without abstention or calibration scoring (2.7, 2.10, 8.2, 8.6), abstains on a vote margin without a scored outcome distribution (8.5), or screens candidates before a live test by offline ranking or replay without scoring a product experiment's outcome (8.1, 8.3, 8.4).
- A decision-value evaluation of choosing which experiments to run from pre-launch information alone, with intervals against random order, on public ledgers. 8.1 chooses which creatives to test from pre-launch information and reports offline recall and one live rank, so the claim is narrowed to public archives of product experiments with proper scoring; 4.6 evaluates rules that consume the experiment's own data; 4.5 changes allocation and thresholds rather than selection.
- The ladder design in which each rung generalizes the previous one (cell base rate, then cell prior, then kernel-weighted precedents shrunk to that prior, then a frozen human forecast, then a stacked second opinion at weight zero) with a leave-one-test-out mixing weight and a rolling-origin backtest over versioned ledger snapshots, so that a rung is admitted only when it beats the rung below out of sample. No verified paper combines these rungs or gates them this way.
- Use of the ASOS checkpoint dataset for pre-launch outcome prediction; all verified uses (6.4, 6.6, 6.7, 6.8) concern sequential testing or bandits.

Risks to the novelty claim that the paper should address directly: 7.1 (comparison-set pooling) and 2.6 plus 2.7 (text-based winner prediction on Upworthy) are close enough that the paper needs head-to-head numbers on matched splits, and 3.4 should be credited as the origin of the base-rate-as-prior idea.

Summary: 79 references fetch-verified (10 in Section 1, 10 in Section 2, 7 in Section 3, 7 in Section 4, 10 in Section 5, 8 in Section 6, 5 in Section 7, 13 in Section 8, 9 in Section 9).
Unverified: 3 (U.1 to U.3); two dataset-usage details in 6.7 and 6.8 are flagged as not confirmed from the fetched page.

Pass 8 (4 November 2026): three sources for the fixed challenger set added after the editorial checklist (the related-work section cites every baseline's source), each fetch-verified today: `pedregosa2011scikit` (Pedregosa et al., Scikit-learn: Machine Learning in Python, Journal of Machine Learning Research 12(85):2825-2830, 2011; page fetched at jmlr.org/papers/v12/pedregosa11a.html), the implementation of all three challengers (HistGradientBoostingRegressor, TfidfVectorizer with LogisticRegression, TruncatedSVD); `friedman2001greedy` (Friedman, Greedy function approximation: A gradient boosting machine, The Annals of Statistics 29(5):1189-1232, 2001; CrossRef record of doi 10.1214/aos/1013203451 fetched); `salton1988term` (Salton and Buckley, Term-weighting approaches in automatic text retrieval, Information Processing and Management 24(5):513-523, 1988; CrossRef record of doi 10.1016/0306-4573(88)90021-0 fetched). Cited in the second paragraph of the related-work section. 81 entries, all cited.

Pass 12 (5 November 2026, round 03, R7 under R5.3): two sources added for the borrowed ideas of Section 4.2, both fetch-verified on 5 November 2026 by the lead. `platt2000probabilities`: the Crossref record of DOI 10.7551/mitpress/1113.003.0008 (https://api.crossref.org/works/10.7551/mitpress/1113.003.0008) gives the chapter as registered, "Probabilities for SV Machines", John C. Platt, in Advances in Large-Margin Classifiers, edited by Smola, Bartlett, Schölkopf and Schuurmans, The MIT Press, published 29 September 2000, pages 61 to 74, ISBN 9780262283977; the longer title "Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods" is the 1999 preprint's and is kept in the entry's note; the chapter is cited for the Platt map of the recalibrated challenger rows. `garreau2017large`: https://arxiv.org/abs/1707.07269 (HTTP 200), "Large sample analysis of the median heuristic", Damien Garreau, Wittawat Jitkrittum and Motonobu Kanagawa, 2017 (version 3, 2018), math.ST and stat.ML, 27 pages, no venue stated, cited as the arXiv preprint for the median heuristic of the kernel bandwidth. The MIT Press, DBLP, Semantic Scholar and Google Books pages refused automated fetches that day; Crossref by DOI answered. 83 entries, all cited.
