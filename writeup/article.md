# How many rounds until you can trust a strokes-gained number?

*Josh Silverman · July 2026 · [Code and data pipeline on GitHub](https://github.com/josh-silverman/sg-reliability)*

In May and June of 2019, Jordan Spieth gained 28.3 strokes on the field
with his putter over 16 rounds, an average of almost +1.8 per round. For
context, that's roughly double the best season-long putting pace of the
past decade. Watching a stretch like that, it's tempting to conclude that
a player has reached a new level. Whether that conclusion is justified is
a question you can actually answer with data, and answering it is what
this project is about.

The question comes down to reliability: how quickly can you trust a
golfer's strokes-gained numbers to represent his true skill level?
Strokes gained (SG) breaks each round into 4 main categories: off the tee
(OTT), approach (APP), around the green (ARG), and putting (PUTT). Every
one of those numbers is a mix of skill and luck, and with a small sample
it's mostly luck. What I wanted to know is how big the sample has to get,
for each category, before the number is telling you something real. I'll
come back to Spieth's streak at the end.

I grew up around baseball, and baseball answered this question years ago.
Sabermetrics has well-known estimates of how many plate appearances each
stat needs before it "stabilizes," and analysts use those numbers every day
to decide how seriously to take a hot start. I wanted the same reference
numbers for golf, with uncertainty attached.

The short version of what I found: after analyzing almost 10 years of PGA
Tour data, around 135K player-rounds, driving (OTT) is by far the most
reliable of the 4 categories. It takes roughly **9 rounds** of driving data
to reach the point where the number is half skill and half noise. Putting
is the least reliable, needing roughly 5 times as much data, around
**48 rounds**, to reach that same point. Approach and around the green fall in between, at
around 30 and 39 rounds.

## Why it matters

Almost every practical use of strokes-gained data depends on how reliable
the underlying sample is:

- **Prediction and betting.** A model that treats a hot month of putting
  the same as a hot month of driving is mostly reacting to noise.
- **Form.** When an announcer says a player is "in form," that claim means
  something different depending on the category and the sample size behind
  it. Twelve rounds of strong driving is mostly real. Twelve rounds of
  strong putting is mostly not.
- **Player evaluation.** Tour cards, team picks, and sponsor exemptions get
  argued from samples that, for some categories, are far too small to
  support the argument.

## The data

I pulled round-level strokes gained in all 4 categories from the
[DataGolf](https://datagolf.com) historical raw data API: every PGA Tour
event with SG tracking from 2017 through mid-2026. That came to 347 events
and 134,951 player-rounds. Another 96 events in that span, mostly
opposite-field and fall events, have no shot tracking and are excluded by
construction.

Cleaning was minimal, and I decided on it before running the analysis. I
dropped the 1.29% of rounds missing SG data (these come from multi-course
events where only the host course is tracked), dropped the Zurich Classic
because it's a two-man team event, and computed total SG as the sum of the
4 categories rather than trusting the provided total column (which has
small, constant per-round offsets in a handful of events). The final
analysis set is 131,847 rounds by 1,772 players.

One discipline I followed in this project: I wrote the full analysis plan
(the questions, the methods, the thresholds, and what I would report no
matter how it came out) and committed it to the repo before computing a
single result. It's there as
[`ANALYSIS_PLAN.md`](https://github.com/josh-silverman/sg-reliability/blob/main/ANALYSIS_PLAN.md),
and everything below is that plan, executed. The whole analysis reproduces
from the repo with one command.

## How I measured reliability

**Split-half reliability.** Take a player's rounds within a two-year
window and deal them randomly into two piles of n rounds each, then average
each pile. If an n-round average really measures skill, a player's two
piles should agree with each other, which means that across all players the
two piles should correlate. That correlation is the reliability, R, of an
n-round average: the share of the differences you see between players that
reflects true skill rather than sampling luck. I computed it for sample
sizes from 5 to 60 rounds, averaging 200 random deals at each size, across
five two-year windows from 2017 to 2026.

**Stabilization curves.** Reliability follows a known one-parameter curve,
R(n) = n / (n + k). This is the same Spearman-Brown form that sabermetrics
uses for stabilization. The constant k is the number to remember: it's the
sample size at which a category's average becomes exactly half skill and
half noise. I fit k for each category and bootstrapped the players (1,000
resamples) to get confidence intervals.

I also ran two checks that don't depend on the fitted curve at all:
year-over-year correlation of season averages (for players with at least 30
tracked rounds in both seasons), and a test of how well each category's
season average predicts the *next* season's total SG.

## What I found

### Driving stabilizes in about 9 rounds, putting in about 48

![Stabilization curves](../figures/stabilization_curves.svg)

> **Key takeaway:** If a player has gained 1.5 strokes per round putting
> over his last 3 tournaments, don't assume he's become one of the best
> putters on tour. At that sample size, about 80% of the number should
> still be treated as noise. The same stretch of driving deserves much
> more trust: closer to 60% of it is signal.

The table below shows the number of rounds until each category's average is
half signal (R = 0.5, which is the fitted k) and mostly signal (R = 0.7),
with bootstrap 95% confidence intervals:

| Category | Half signal (R = 0.5) | Mostly signal (R = 0.7) |
|---|---|---|
| Off the tee | **8.7** [7.9, 9.7] | 20 [19, 22] |
| Total SG | 23 [20, 27] | 54 [47, 63] |
| Approach | 30 [26, 34] | 69 [60, 80]* |
| Around the green | 39 [36, 44] | 92 [83, 103]* |
| Putting | **48** [42, 54] | 111 [98, 125]* |

\* beyond the measured range of the data (n = 60), so read these as fitted
extrapolations.

To put those numbers in context: a full-time PGA Tour player gets roughly
70 to 90 tracked rounds in a season. That means putting never reaches
R = 0.7 within a single season. Two tournaments of driving data tell you
more about a player's tee game than a full season of putting data tells you
about his putting. Approach play is still a strong skill signal, it just
needs about 3 times as much data as driving before you can trust it to the
same degree.

### A check that doesn't depend on the model

![Year-over-year scatter](../figures/yoy_scatter.svg)

Correlating consecutive season averages needs no fitted curve, and across
1,309 player-season pairs it produces the same ordering: OTT at 0.72, APP
at 0.59, ARG at 0.56, and PUTT at 0.49. Rank correlations agree. Another
way to say that last number: half of what looks like putting skill over a
full season doesn't carry over to the next one.

### What to do with a hot streak

![Shrinkage meter](../figures/shrinkage_meter.svg)

Reliability translates directly into how much you should trust a sample.
R is the weight the sample deserves, and the rest of your estimate should
come from the tour average. To put this in practical terms, if you're
trying to estimate a player's true putting skill from his last 12 rounds,
you should only give that sample about 20% weight. The remaining 80% is
better estimated by the tour average, since most of a short-term putting
streak turns out to be noise. The same 12 rounds of driving data deserve
about 58% weight, approach about 29%, and around the green about 23%.

The forward-looking version tells the same story. Predicting next season's
total SG from this season's category averages, driving is the best single
predictor (r = 0.43), approach is close behind (0.40), and putting is far
last (0.16). In a joint regression putting recovers some value
(standardized beta of 0.26 versus its 0.16 univariate correlation), which
is worth being precise about: putting skill exists and matters, but a
season of putting data measures that skill badly.

### Reliability depends on who you're comparing

One result I didn't pre-register but need to report. The main curves use
every player with enough rounds at each sample size, which means the
small-sample estimates include the full range of tour talent while the
large-sample estimates skew toward regulars. When I re-ran the entire
analysis on a fixed pool, only the 386 player-windows with 120 or more
rounds, reliability dropped across the board: k rose to around 14 for
driving and around 43 to 48 for the other 3 categories, and approach's edge
over putting nearly disappeared. The ordering held, with driving fastest
and putting slowest.

The lesson is that reliability is always relative to the group you're
comparing within. Distinguishing a tour regular from a part-time player is
relatively easy, and small samples can do it. Distinguishing tour regulars
from each other is much harder, and for every category except driving,
small samples mostly can't.

## Practical implications

Statistics are useful, but they're easier to understand when you see them
applied to a real player. So let's come back to Jordan Spieth's putting
run from the opening.

That stretch in May and June of 2019 was the hottest putting run in this
sample. In fact, the single best 12-round putting window by any player in
all 131,847 rounds sits inside it. It covered 16 rounds across 4 straight
events: the AT&T Byron Nelson, the PGA Championship, the Charles Schwab
Challenge, and the Memorial. Spieth averaged +1.77 per round with the
putter over those 16 rounds, and he finished T3, T8, and T7 in the last 3
of those events.

My analysis found that putting doesn't become a reasonably reliable
measure of skill until roughly 48 rounds. Since this streak only lasted 16
rounds, we shouldn't believe all of it. The math says a 16-round sample
earns a weight of 16 / (16 + 48), which comes out to about 25%. In other
words, most of this hot streak should still be treated as random variation
rather than evidence that Spieth suddenly became a historically great
putter. That puts the honest estimate of his true putting skill at that
moment at about +0.44 per round: still clearly good, but a quarter of what
the streak suggested.

Looking back, that's almost exactly what happened. Over his next 30
tracked rounds, Spieth gained +0.69 per round with the putter. Over the
486 tracked rounds he has played since the streak ended, he has gained
+0.10 per round, almost identical to his +0.13 average in the 154 rounds
before it started. His putting quickly returned to the level he had
maintained before the streak. If a prediction model had simply assumed his
+1.77 strokes per round represented his new normal, it would have
dramatically overestimated his future performance. The reliability
analysis pointed to a much more realistic expectation.

Driving behaves differently, and a matching example shows why the same
rule can't be applied to every category. In February and March of 2022,
Jon Rahm averaged +1.47 strokes per round off the tee across 12 rounds (the
WM Phoenix Open, the Genesis Invitational, and the Arnold Palmer
Invitational). Driving becomes half signal at around 9 rounds, so a
12-round sample keeps about 58% of its value, for a predicted true skill of
about +0.85 per round. Over his next 30 rounds, Rahm gained +0.90 per round
off the tee. The hot month of driving was mostly real, and the regressed
estimate was nearly exact.

More generally:

- **Trust early driving numbers.** Around 9 rounds of SG:OTT is real
  information. Driving is also the most persistent skill year over year and
  the best single predictor of future total SG.
- **Heavily regress short-term putting.** Keep about 20% of a 12-round
  putting streak and let the tour average carry the rest.
- **Ask "which category?" before believing a form claim.** The same
  three-event stretch can be majority signal for driving and roughly
  three-quarters noise for putting.
- **Season-long total SG is dependable by about half a season.** Total SG
  reaches R = 0.5 at around 23 rounds, faster than 3 of its 4 components,
  because every shot in a round contributes to it.

That's the central takeaway of this research. The same number of rounds
can tell us very different things depending on what we're measuring. A
12-round putting streak and a 12-round driving streak might look equally
impressive on paper, but the evidence suggests they should be interpreted
very differently.

## Limitations

Strokes-gained data only exists at shot-tracked events, so fall and
opposite-field golf is invisible here. The two-year windows assume a
player's skill is stable within them; real skill change gets counted as
noise, which means these k values are, if anything, slightly pessimistic.
The R = 0.7 estimates for approach, around the green, and putting
extrapolate beyond the measured range (the fitted curve is very accurate
within it). Reliability is relative to the comparison group, as covered
above. The 2020 season was shortened and disrupted. Course fit and field
strength are averaged over, not modeled.

## Appendix: formulas and reproducibility

Split-half reliability at n: r = corr(x̄₁, x̄₂) across players, where x̄₁ and
x̄₂ are means of disjoint random n-round halves; reported R(n) averages 200
splits. Stabilization: least-squares fit of R(n) = n/(n+k) over
n ∈ {5,…,60}; k is the R = 0.5 crossing and 7k/3 is the R = 0.7 crossing.
Confidence intervals: percentile bootstrap, 1,000 resamples of
player-windows, seed 42. Shrinkage weight for an n-round sample: n/(n+k).
Everything, including the Spieth and Rahm example numbers, regenerates
from the scripts in `scripts/` (`fetch_data.py`, `run_analysis.py`,
`hot_streak_example.py`, `make_figures.py`); the analysis module has a
test suite validated against synthetic data with known reliability.

*Data from the DataGolf API, used per their terms (the pipeline is public;
the raw data is not redistributed).*
