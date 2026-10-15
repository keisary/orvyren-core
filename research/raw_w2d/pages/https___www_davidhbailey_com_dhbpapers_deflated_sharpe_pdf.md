# https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf

# THE DEFLATED SHARPE RATIO: CORRECTING FOR SELECTION BIAS, BACKTEST OVERFITTING AND NON-NORMALITY

David H. Bailey †

‡
Marcos López de Prado

First version: April 15, 2014
This version: July 31, 2014

**_Journal of Portfolio Management, Forthcoming, 2014_**

†
Recently retired from Lawrence Berkeley National Laboratory, Berkeley, CA 94720. Research Fellow at the
University of California, Davis, Department of Computer Science. E-mail: [david@davidhbailey.com](mailto:david@davidhbailey.com)

‡
Senior Managing Director, Guggenheim Partners, New York, NY 10017. Research Affiliate, Computational
Research Division, Lawrence Berkeley National Laboratory, Berkeley, CA 94720. E-mail: [lopezdeprado@lbl.gov](mailto:lopezdeprado@lbl.gov)

Special thanks are owed to Prof. David J. Hand (Royal Statistical Society), who reviewed an early version of this
paper and suggested various extensions. We are also grateful to Matthew Beddall (Winton Capital), José Blanco
(Credit Suisse), Jonathan M. Borwein (University of Newcastle, Australia), Sid Browne (Credit Suisse), Peter Carr
(Morgan Stanley, NYU), Marco Dion (J.P. Morgan), Matthew D. Foreman (University of California, Irvine),
Stephanie Ger (Berkeley Lab), Campbell Harvey (Duke University), Kate Land (Winton Capital), Jeffrey S. Lange
(Guggenheim Partners), Attilio Meucci (KKR, NYU), Philip Protter (Columbia University), Riccardo Rebonato
(PIMCO, University of Oxford), Mark Roulston (Winton Capital), Luis Viceira (HBS), John Wu (Berkeley Lab) and
Jim Qiji Zhu (Western Michigan University).

The statements made in this communication are strictly those of the authors and do not represent the views of
Guggenheim Partners or its affiliates. No investment advice or particular course of action is recommended. All
rights reserved.

* * *

# THE DEFLATED SHARPE RATIO: CORRECTING FOR SELECTION BIAS, BACKTEST OVERFITTING AND NON-NORMALITY

## ABSTRACT

With the advent in recent years of large financial data sets, machine learning and highperformance computing, analysts can backtest millions (if not billions) of alternative investment
strategies. Backtest optimizers search for combinations of parameters that maximize the
simulated historical performance of a strategy, leading to _backtest overfitting._

The problem of performance inflation extends beyond backtesting. More generally, researchers
and investment managers tend to report only positive outcomes, a phenomenon known as
_selection bias._ Not controlling for the number of trials involved in a particular discovery leads to
over-optimistic performance expectations.

The _Deflated Sharpe Ratio_ (DSR) corrects for two leading sources of performance inflation:
Selection bias under multiple testing and non-Normally distributed returns. In doing so, DSR
helps separate legitimate empirical findings from statistical flukes.

Keywords: Sharpe ratio, Non-Normality, Probabilistic Sharpe ratio, Backtest overfitting,
Minimum Track Record Length, Minimum Backtest Length.

JEL Classification: G0, G1, G2, G15, G24, E44.
AMS Classification: 91G10, 91G60, 91G70, 62C, 60E.

* * *

Today’s quantitative teams routinely scan through petabytes of financial data, looking for
patterns invisible to the naked eye. In this endeavor, they are assisted by a host of technologies
and advancing mathematical fields. Big data, machine learning, cloud networks and parallel
processing have meant that millions (if not billions) of analyses can be carried out on a given
dataset, searching for profitable investment strategies. To put this in perspective, the amount of
data used by most quant teams today is comparable to the memory stored by Netflix to support
its video-streaming business nationwide. This constitutes a radical change compared to the
situation a couple of decades ago, when the typical financial analyst would run elementary
arithmetic calculations on a spreadsheet containing a few thousand datapoints. In this paper we
will discuss some of the unintended consequences of utilizing scientific techniques and highperformance computing without controlling for selection bias. While these problems are not
specific to finance, examples are particularly abundant in financial research.

Backtests are a case in point. A backtest is a historical simulation of how a particular investment
strategy would have performed in past. Although backtesting is a powerful and necessary
research tool, it can also be easily manipulated. In this article we will argue that the most
important piece of information missing from virtually all backtests published in academic
journals and investment offerings is the number of trials attempted. Without this information, it
is impossible to assess the relevance of a backtest. Put bluntly, _a backtest where the researcher_
_has not controlled for the extent of the search involved in his or her finding is worthless,_
_regardless of how excellent the reported performance might be._ Investors and journal referees
should demand this information whenever a backtest is submitted to them, although even this
will not remove the danger completely.

## MULTIPLE TESTING

Investment strategies are typically judged according to performance statistics. Because any
measurement is associated with a margin of error, the process of selecting a statistical model is
an instance of decision-making under uncertainty. We can never be certain that the true
performance is above a certain threshold, even if the estimated performance is. Two sorts of
errors arise: The _Type I Error,_ with probability (also called “significance level”), and the _Type_
_II Error,_ with probability . The Type I Error occurs when we choose a strategy that should have
been discarded (a “false positive”), and the Type II Error occurs when we discard a strategy that
should have been chosen (a “false negative”). Decision makers are often more concerned with
“false positives” than with “false negatives”. The reason is, they would rather exclude a true
strategy than risking the addition of a false one. For risk-averse investors, a lost opportunity is
less worrisome than an actual loss. For this reason, the standard practice is to design statistical
tests which set the Type I Error probability to a low threshold (e.g., ), while maximizing
the power of the test, defined as .

$$
1-\\beta
$$

Suppose now that we are interested in analyzing multiple strategies on the same dataset, with the
aim of choosing the best, or at least a good one, for future application. A curious problem then
emerges: As we test more and more strategies, each at the same significance level , the overall
probability of choosing at least one poor strategy grows. This is called the multiple testing
problem, and it is so pervasive and notorious that the American Statistical Society explicitly
warns against it its Ethical Guidelines (American Statistical Association, 1997, guideline #8):

* * *

_Running multiple tests on the same data set at the same stage of an analysis_
_increases the chance of obtaining at least one invalid result. Selecting the one_
_“significant” result from a multiplicity of parallel tests poses a grave risk of an_
_incorrect conclusion. Failure to disclose the full extent of tests and their results in_
_such a case would be highly misleading._

## SELECTION BIAS

Researchers conducting multiple tests on the same data tend to publish only those that pass a
statistical significance test, hiding the rest. Because negative outcomes are not reported, investors
are only exposed to a biased sample of outcomes. This problem is called “selection bias”, and it
is caused by multiple testing combined with partial reporting, see Roulston and Hand \[2013\]. It
appears in many different forms: Analysts who do not report the full extent of the experiments
conducted (“file drawer effect”), journals that only publish “positive” outcomes (“publication
bias”), indices that only track the performance of hedge funds that didn’t blow up (“survivorship
bias”), managers who only publish the history of their (so far) profitable strategies (“selfselection bias”, “backfilling”), etc. What all these phenomena have in common is that critical
information is hidden from the decision-maker, with the effect of a much larger than anticipated
Type I Error probability. Ignoring the full extent of trials makes the improbable more probable,
see Hand \[2014\].

The danger of encountering false positives is evident in High-Throughput Screening (HTS)
research projects, such as those utilized to discover drug treatments, the design of chemical
compounds or microarrays genetic testing. Bennett et al. \[2010\] were awarded the 2012 Ig Nobel
prize for showing that even a salmon’s dead brain can appear to show significant activity under
multiple MRI testing. More seriously, the pharmaceutical field has been stung with numerous
recent instances of products that look great based on published trials, but which disappoint when
actually fielded. The problem here, in many cases, is that only the results of successful tests are
typically published, thereby introducing a fundamental bias into the system. Such experiences
have led to the AllTrials movement (see [http://alltrials.net](http://alltrials.net/)), which would require the results of all
trials to be made public.

In spite of the experience of HTS projects, it is rare to find financial studies that take into
account the increased false positive rates that result from hiding multiple testing. The extent of
this problem has led some researchers to paraphrase Ioannidis \[2005\] and conclude that “most
claimed research findings in financial economics are likely false”, see Harvey et al. \[2013\].

## BACKTEST OVERFITTING

What constitutes a legitimate empirical finding? After a sufficient number of trials, it is
guaranteed that a researcher will always find a misleadingly profitable strategy, a false positive.
Random samples contain patterns, and a systematic search through a large space of strategies
will eventually lead to identifying one that profits from the chance configuration of how the
random data have fallen. When a set of parameters are optimized to maximize the performance
of a backtest, an investment strategy is likely to be fit to such flukes. This phenomenon is called

* * *

“backtest overfitting”, and we refer the reader to Bailey et al. \[2014\] for a detailed discussion.
Although the historical performance of an optimized backtest may seem promising, the random
pattern that fuels it is unlikely to repeat itself in the future, hence rendering the strategy
worthless. Structural breaks have nothing to do with the failure of the strategy in this situation.

Let us elucidate this point with an example. After tossing a fair coin ten times we could obtain by
chance a sequence such as {+,+,+,+,+,-,-,-,-,-}, where “+” means head and “-” means tail. A
researcher could determine that the best strategy for betting on the outcomes of this coin is to
expect “+” on the first five tosses, and for “-” on the last five tosses (a typical “seasonal”
argument in the investment community). When we toss that coin ten more times, we may obtain
a sequence such as {-,-,+,-,+,+,-,-,+,-}, where we win 5 times and lose 5 times. That researcher’s
betting rule was overfit, because it was designed to profit from a random pattern present only in
the past. The rule has null power over the future, regardless of how well it appears to have
worked in the past.

Competition among investment managers means that the ratio of signal to noise in financial
series is low, increasing the probability of “discovering” a chance configuration, rather than an
actual signal. The implication is that backtest overfitting is hard to avoid. Clearly this is a critical
issue, because most investment decisions involve choosing among multiple candidates or
alternatives.

## AN ONLINE TOOL TO EXPLORE BACKTEST OVERFITTING


[... middle omitted — see footer ...]

    2012b).

06. Beddall, M. and K. Land. “The hypothetical performance of CTAs”. Working paper,
    Winton Capital Management (2013).

07. Benjamini, Y. and Y. Hochberg. “Controlling the false discovery rate: A practical and
    powerful approach to multiple testing.” Journal of the Royal Statistical Society, Series B
    (Methodological), Vol. 57, No. 1 (1995), pp. 289 - 300.

08. Bennet, C., A. Baird, M. Miller and G. Wolford. “Neural Correlates of Interspecies
    Perspective Taking in the Post-Mortem Atlantic Salmon: An Argument For Proper
    Multiple Comparisons Correction”, Journal of Serendipitous and Unexpected Results,
    Vol. 1, No. 1 (2010), pp. 1-5.

09. Bruss, F. “A unified Approach to a Class of Best Choice problems with an Unknown
    Number of Options”. Annals of Probability, Vol. 12, No. 3 (1984), pp. 882–891.

10. Dmitrienko, A., A.C. Tamhane, and F. Bretz (eds.) Multiple Testing Problems in
    Pharmaceutical Statistics. 1st edition, Boca Raton, FL: CRC Press, 2010.

11. Dudoit, S. and M.J. van der Laan. Multiple Testing Procedures with Applications to
    Genomics. 1st edition, Berlin: Springer, 2008.

12. Fisher, R.A. “Frequency distribution of the values of the correlation coefficient in
    samples of an indefinitely large population.” Biometrika (Biometrika Trust), Vol. 10, No.
    4 (1915), pp. 507–521.

13. Hand, D. J. The Improbability Principle. 1st edition, New York, NY: Scientific
    American/Farrar, Straus and Giroux, 2014.

14. Harvey, C., Y. Liu and H. Zhu. “…And the Cross-Section of Expected Returns.”
    Working paper, Duke University, 2013. Available at: [http://ssrn.com/abstract=2249314](http://ssrn.com/abstract=2249314)

15. Harvey, C. and Y. Liu. “Backtesting.” Working paper, Duke University, 2014. Available
    at [http://ssrn.com/abstract=2345489](http://ssrn.com/abstract=2345489)

16. Hochberg Y. and A. Tamhane. Multiple comparison procedures. 1st edition, New York,
    NY: Wiley, 1987.

17. Holm, S. “A Simple sequentially rejective multiple test procedure.” Scandinavian Journal
    of Statistics, Vol. 6 (1979), pp. 65-70.


* * *

18. Ioannidis, J.P.A. “Why most published research findings are false.” PloS Medicine, Vol.
    2, No. 8 (2005), pp. 696-701.

19. Ingersoll, J., M. Spiegel, W. Goetzmann, I. Welch. “Portfolio performance manipulation
    and manipulation-proof performance measures.” The Review of Financial Studies, Vol.
    20, No. 5 (2007), pp. 1504-1546.

20. Lo, A. “The Statistics of Sharpe Ratios.” Financial Analysts Journal, Vol. 58, No. 4
    (July/August 2002), pp. 36-52.

21. López de Prado, M., A. Peijan. “Measuring Loss Potential of Hedge Fund Strategies.”
    Journal of Alternative Investments, Vol. 7, No. 1 (Summer, 2004), pp. 7-31.
    [http://ssrn.com/abstract=641702](http://ssrn.com/abstract=641702)

22. Mertens, E. “Variance of the IID estimator in Lo (2002).” Working paper, University of
    Basel, 2002.

23. Roulston, M. and D. Hand. “Blinded by Optimism.” Working paper, Winton Capital
    Management, December 2013.

24. Schorfheide, F. and K. Wolpin. “On the Use of Holdout Samples for Model Selection.”
    American Economic Review, Vol. 102, No. 3 (2012), pp. 477-481.

25. Sharpe, W. “Mutual Fund Performance.” Journal of Business, Vol. 39, No. 1 (1966), pp.
    119–138.

26. Sharpe, W. “Adjusting for Risk in Portfolio Performance Measurement.” Journal of
    Portfolio Management, Vol. 1, No. 2 (Winter, 1975), pp. 29-34.

27. Sharpe, W. “The Sharpe ratio.” Journal of Portfolio Management, Vol. 21, No. 1 (Fall,
    1994), pp. 49-58.

28. Studený M. and Vejnarová J. “The multiinformation function as a tool for measuring
    stochastic dependence.” in M I Jordan, ed., Learning in Graphical Models, Cambridge,
    MA: MIT Press, 1999, pp. 261–296,

29. Watanabe S. “Information theoretical analysis of multivariate correlation.” IBM Journal
    of Research and Development, Vol. 4 (1960), pp. 66–82.

──────── [TRUNCATED] ────────
Showing 11,914 chars (head) + 3,938 chars (tail) of 53,943 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\www.davidhbailey.com-8ff3cf4021.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\www.davidhbailey.com-8ff3cf4021.md" offset=183 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────