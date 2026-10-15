Judgment and Decision Making, Vol. 13, No. 6, November 2018, pp. 607–621

Boosting intelligence analysts’ judgment accuracy: What works, what
fails?

David R. Mandel∗
Christopher W. Karvetski†
Mandeep K. Dhami‡

Abstract

A routine part of intelligence analysis is judging the probability of alternative hypotheses given available evidence. Intelli-
gence organizations advise analysts to use intelligence-tradecraft methods such as Analysis of Competing Hypotheses (ACH)
to improve judgment, but such methods have not been rigorously tested. We compared the evidence evaluation and judgment
accuracy of a group of intelligence analysts who were recently trained in ACH and then used it on a probability judgment task
to another group of analysts from the same cohort that were neither trained in ACH nor asked to use any specific method.
Although the ACH group assessed information usefulness better than the control group, the control group was a little more
accurate (and coherent) than the ACH group. Both groups, however, exhibited suboptimal judgment and were susceptible to
unpacking effects. Although ACH failed to improve accuracy, we found that recalibration and aggregation methods substan-
tially improved accuracy. Specifically, mean absolute error (MAE) in analysts’ probability judgments decreased by 61% after
first coherentizing their judgments (a process that ensures judgments respect the unitarity axiom) and then aggregating their
judgments. The findings cast doubt on the efficacy of ACH, and show the promise of statistical methods for boosting judgment
quality in intelligence and other organizations that routinely produce expert judgments.

Keywords: probability judgment, accuracy, coherence, intelligence analysis, recalibration, aggregation, coherentization

1
Introduction

Intelligence organizations routinely call upon their analysts
to make probability judgments and test hypotheses under
conditions of uncertainty. These expert judgments can in-
form important policy decisions concerning national and
international security. Traditionally, analysts have been ex-
pected to accumulate domain expertise and apply this along
with critical thinking skills to arrive at timely and accurate
assessments for decision-makers. In the US, developers of
analytic tradecraft (i.e., the methods developed within the in-
telligence community to support its analytic functions) such
as Richards Heuer Jr. and Jack Davis introduced so-called
“structured analytic techniques” (SATs) to support the ana-
lyst in the assessment process, but these methods were largely
optional tricks-of-the-trade. That state of affairs changed fol-
lowing two notable geopolitical events (i.e., the September

This research was supported by Department of National Defence project
#05da, Canadian Safety and Security Program projects #2016–TI–2224 and
#2018–TI–2394, and HM Government. This work contributes to the NATO
System Analysis and Studies Panel Research Task Group on Assessment and
Communication of Uncertainty in Intelligence to Support Decision Making
(SAS-114). We thank Jon Baron, Jonathan Nelson, and two anonymous
reviewers for helpful feedback on this research.
Copyright: © 2018. The authors license this article under the terms of
the Creative Commons Attribution 3.0 License.
∗Intelligence,
Influence and Collaboration Section,
Toronto Re-
search Centre, Defence Research and Development Canada.
Email:
drmandel66@gmail.com.
†BlackSwan Technologies Ltd.
‡Department of Psychology, Middlesex University.

11, 2001, terrorist attacks by Al Qaeda and the 2003 invasion
of Iraq) that were attributed in part to striking intelligence
failures. These events prompted reviews of the intelligence
community with ensuing organizational reforms that, among
other things, aimed at debiasing intelligence analysts’ judg-
ments (Belton & Dhami, in press). In the US, the Intelligence
Reform and Terrorism Prevention Act of 2004 mandated the
use of SATs in intelligence production and SATs became a
staple topic in most analytic training programs (Chang, Ber-
dini, Mandel & Tetlock, 2018; Coulthart, 2017; Marchio,
2014). Much the same set of organizational reforms was en-
acted in other Western countries such as the UK (e.g., Butler,
2004).
Although the number of SATs has skyrocketed over the last
decade (Dhami, Belton & Careless, 2016; Heuer & Pherson,
2014), as others have lamented in recent years (Chang et al.,
2018; Dhami, Mandel, Mellers & Tetlock, 2015; National
Research Council, 2011; Pool, 2010), there has been little
effort to test their effectiveness. Instead, most SATs have
been adopted on the basis of their perceived face validity
with the belief that, although imperfect, they must be better
than nothing. At the same time, the intelligence commu-
nity has rarely considered using post-analytic techniques to
improve judgment (Mandel & Tetlock, 2018). For instance,
Mandel and Barnes (2014) showed that intelligence analysts’
strategic forecasts were underconfident, but that much of this
bias could be eliminated by recalibrating their judgments to
make them more extreme (also see Baron, Mellers, Tetlock,
Stone & Ungar, 2014; Turner, Steyvers, Merkle, Budescu

607

https://doi.org/10.1017/S1930297500006628 Published online by Cambridge University Press


Judgment and Decision Making, Vol. 13, No. 6, November 2018
Boosting intelligence analysts’ judgment accuracy
608

& Wallsten, 2014).
Similarly, the accuracy of probabil-
ity judgments can be improved post-judgment by recalibra-
tion so judgments respect one or more coherence principles,
such as the axioms of probability calculus — a statistical
process called coherentization (Karvetski, Olson, Mandel &
Twardy, 2013). Karvetski et al. further observed that weight-
ing individuals’ contributions to aggregated judgments also
improved accuracy above the gains achieved using an un-
weighted arithmetic average.
In the present research, we
examine the accuracy of intelligence analysts’ probability
judgments in an experimental task. We examine the effec-
tiveness of ACH as well as recalibration and aggregation
methods with the aim of addressing the prescriptive ques-
tion: what works — and what fails — to improve judgment
accuracy?

1.1
The Analysis of Competing Hypotheses
Technique

The Analysis of Competing Hypotheses (ACH; Heuer, 1999;
Heuer & Pherson, 2014) is one of the most widely known
SATs, and one of only nine that is listed in the US Govern-
ment’s (2009) Tradecraft Primer (also see UK Ministry of
Defence, 2013). The US Government describes ACH as a
diagnostic technique whose main function is to externalize
analytic hypotheses and evidence. It further claims that ACH
helps analysts overcome common cognitive biases, such as
primacy effects, confirmation bias, and other forms of pre-
mature cognitive closure that can undermine the accuracy of
forecasts or other probabilistic assessments. The US Gov-
ernment also asserts that ACH “has proved to be a highly
effective technique when there is a large amount of data to
absorb and evaluate” (2009, p. 14), yet it does not cite any
evidence to support that claim. The UK handbook conveys
comparable exuberance for ACH, noting, “The approach is
designed to help analysts consider all the evidence in the
light of all the hypotheses as objectively as possible” (UK
Ministry of Defence, 2013, p. 14, italics added).
ACH includes several steps, but the core of the trade-
craft method involves generating a matrix in which mutually
exclusive and (preferably) collectively exhaustive (MECE)
hypotheses are listed in columns and pieces of relevant ev-
idence are listed in rows.
The analyst then assesses the
consistency of each piece of evidence with each hypothesis
starting on the first row and moving across the columns. For
each cell, the analyst rates evidence-hypothesis consistency
on a 5-point ordinal scale (i.e., −2 = highly inconsistent, −1
= inconsistent, 0 =neutral or not applicable, 1 = consistent,
2 = highly consistent. However, only the negative scores
(−1 and −2) are tallied for each hypothesis. For instance,
if there were five pieces of information (i.e., five rows) and
Hypothesis A had ratings {2, 2, 2, 2, −2} and Hypothesis B
had ratings {0, 0, 1, 0, −1}, Hypothesis B with an inconsis-
tency score of −1 would be rated as more likely to be true

than Hypothesis A with a score of −2. In other words, ACH
requires that analysts disregard evidential support for hy-
potheses in the information integration process. This feature
of the method may have been motivated by a misapplication
of Popper’s (1959) ideas about the merits of falsification as
a strategy for scientific discovery. Popper’s claim that hy-
potheses could only be falsified but never proven pertained to
universal hypotheses such as “all swans are white” because
a single non-white swan is sufficient to disprove the claim.
Most hypotheses of interest in intelligence, however, are not
universal but rather deal with events in a particular context
(e.g., Iran is developing a nuclear weapon), and few could be
falsified outright by a single disconfirming piece of evidence
(Mandel, in press).
ACH also includes a subsequent evidential editing phase:
once the matrix is populated with consistency ratings, the an-
alyst is encouraged to remove evidence that does not appear
to differentiate between the alternative hypotheses. However,
there is virtually no guidance on how such assessments of in-
formation usefulness should be conducted. For instance, the
US Government merely instructs, “The ‘diagnostic value’
of the evidence will emerge as analysts determine whether
a piece of evidence is found to be consistent with only one
hypothesis, or could support more than one or indeed all
hypotheses. In the latter case, the evidence can be judged as
unimportant to determining which hypothesis is more likely
correct” (2009, p. 15). The UK handbook is more precise,
stating “For each hypothesis ask the following question: ‘If
this hypothesis were true, how likely would the evidence
be?’” (UK Ministry of Defence, 2013, p. 15; see also Heuer,
1999). Yet, it vaguely advises analysts to “pay most attention
to the most diagnostic evidence — i.e., that which is highly
consistent with some hypotheses and inconsistent with oth-
ers” (p. 17). If evidence is subsequently disregarded, then
analysts are expected to recalculate the sum of the negative
(inconsistency) ratings. These scores are then meant to re-

[... middle omitted — see footer ...]

the simpler form.

0.03 rather than 0.06.4 This analysis suggests that probability
judgments were in the right range, but they were conveying
very little information about the relative probabilities of the
four hypotheses, this reducing the power of the experiment
to detect group differences.

3.5
Aggregating probability judgments

Coherentization yielded a large improvement in the accu-
racy of analysts’ probability judgments. We examined how
much further improvement in accuracy might be achieved by
aggregating analysts’ probability judgments. To do so, we
generated 1,000 bootstrap samples of statistical group sizes
ranging from 1 (i.e., no aggregation) to 49 in increments of
two. We aggregated probability judgments in two ways: us-
ing an unweighted arithmetic average of coherentized proba-
bility judgments and using a coherence-weighted average of
such estimates.5 We examined the effect of aggregation on
MAE as well as on the average Spearman correlation between
the aggregated estimates and the vector of values from the
naïve Bayes model. As a benchmark, we also examined the
effect of these aggregation methods on random responses,
where each data point is based on 1,000 simulations of prob-
ability judgments from a uniform distribution over the [0, 1]
interval.

4Jon Baron conducted this analysis and used normalization (i.e., dividing
each stated probability by the sum of the four) rather than coherentization
as the recalibration method.
5For coherence-weighted aggregation, β = 5. However, as shown in the
supplementary figure, the effect of coherence weighting was robust across
a wide parametric range.

https://doi.org/10.1017/S1930297500006628 Published online by Cambridge University Press


Judgment and Decision Making, Vol. 13, No. 6, November 2018
Boosting intelligence analysts’ judgment accuracy
616

0.4

0.5

0.6

0.7

2
4
6
8
10
Group Size

Probability of Improvement in MAE Over n−1 Group Size

analyst
random

Figure 2: Probability of improvement achieved by increasing group size by one member. Bars show 95% confidence intervals
from 1,000 bootstrap samples. The reference line shows the probability of improvement by chance.

As Figure 1 shows, these analyses yield several impor-
tant findings.
First, they confirm that, when aggregated,
analysts’ judgments are substantially more accurate than ag-
gregated random judgments. Second, it is evident from the
left panel in Figure 1 that aggregation greatly improves ac-
curacy in analysts’ judgments, but to a degree comparable
to that observed in the randomly generated response data.
This suggests that most of the error reduction observed is
due to variance reduction from averaging and should not be
attributed to an eking out of any crowd wisdom, as clearly
there is no wisdom in the random response data.6 Third,
it is equally evident from the right panel in Figure 1 that
aggregation over increasingly larger group sizes steadily in-
creases the correct rank ordering of probabilities. This effect
is clearly not manifested in random response data, where
aggregation has no benefit. Fourth, aggregation with coher-
ence weighting did not outperform aggregation with equal
weighting; in fact, it slightly underperformed. Finally, the
left panel in Figure 1 shows that most error reduction due to
aggregation was achieved with small group sizes. Figure 2
clarifies that there

..._This content has been truncated to stay below 50000 characters_...

──────── [TRUNCATED] ────────
Showing 10,459 chars (head) + 3,448 chars (tail) of 50,072 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\www.cambridge.org-9a54297f32.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\www.cambridge.org-9a54297f32.md" offset=198 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────