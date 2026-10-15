# https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html

[Skip to main content](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#content)

![US Flag](https://www.federalreserve.gov/images/icon-us-flag.svg)

An official website of the United States Government

Here's how you know![Expand More](https://www.federalreserve.gov/images/expand_more.svg)

![.gov icon](https://designsystem.digital.gov/assets/img/icon-dot-gov.svg)

**Official websites use .gov**

A **.gov** website belongs to an official government organization in the United States.

![HTTPS icon](https://designsystem.digital.gov/assets/img/icon-https.svg)

**Secure .gov websites use HTTPS**

A **lock** (LockLocked padlock icon) or **https://** means you've safely connected to the .gov website. Share sensitive information only on official, secure websites.

Main Menu Toggle ButtonSectionsSearch Toggle Button

SearchSearch Submit ButtonSubmit

1. [Home](https://www.federalreserve.gov/default.htm)
2. [Economic Research](https://www.federalreserve.gov/econres.htm)
3. [FEDS Notes](https://www.federalreserve.gov/econres/notes/feds-notes/default.htm)
4. [2025](https://www.federalreserve.gov/econres/notes/feds-notes/2025-index.htm)

## FEDS Notes

[Twitter](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html) [Share](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#)

[RSS](https://www.federalreserve.gov/feeds/feds_notes.xml)

December 17, 2025

### In the Shadow of Bank Runs: Lessons from the Silicon Valley Bank Failure and Its Impact on Stablecoins

[Chuan Du](https://www.federalreserve.gov/econres/chuan-du.htm), [Ria Sonawane](https://www.federalreserve.gov/econres/ria-s-sonawane.htm), and [Cy Watsky](https://www.federalreserve.gov/econres/cy-h-watsky.htm)

#### Summary

Stablecoins are crypto-assets designed to maintain a stable value against a reference asset, typically the U.S. Dollar. The peg to the dollar is supported by the assets that back the stablecoin. Stablecoins perform dollar-like functions in decentralized finance ("DeFi") and represent a run-able liability for their issuers. As with money market funds and bank deposits, stablecoins are susceptible to crises of confidence, contagion, and self-reinforcing runs.

In this note we utilize a granular dataset to document the market stress experienced by USDC, the second largest stablecoin by market cap, during the Silicon Valley Bank ("SVB") crisis of March 2023. SVB was a traditional bank that failed due to inadequate risk management practices. [1](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#fn1 "footnote 1") The bank experienced a rapid run of deposits and was taken into receivership by the Federal Deposit Insurance Corporation ("FDIC").

Shortly after, Circle, the issuer of USDC, publicly announced that it was unable to access a portion of its dollar reserves held as (uninsured) deposits at SVB. This announcement precipitated a surge in redemption requests by holders of USDC, causing the stablecoin to lose its peg against the dollar on secondary markets when Circle shut down primary market operations over the weekend.

We identify a key channel of contagion in the DeFi sector, illustrative of the potential for code-based financial products to amplify stress. At the same time during the resolution of SVB, a crypto-collateralized stablecoin, Dai, was operating one-to-one exchange facilities — called Peg Stability Modules ("PSMs") — against USDC and other stablecoins. [2](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#fn2 "footnote 2") Over the weekend, these PSMs were rapidly drained of liquidity. Dai, and other stablecoins with otherwise no exposure to SVB, also lost their peg to the dollar. Both the SVB run and the stablecoins depegs were ameliorated when the FDIC, the Treasury Department, and the Federal Reserve Board jointly announced that all depositors in SVB would be fully protected.

We highlight three aspects of this USDC depeg episode.

First, there is a potential for two-way feedback between the traditional and the DeFi sectors. In this event, the run on SVB was the trigger for the USDC depeg, which then sparked a broader sell-off in other stablecoins. Intervention designed to backstop SVB stemmed the selling pressure on the affected stablecoins while the USDC primary market was closed. But had the run unfolded differently, the pressure for USDC redemptions might have forced Circle to liquidate backing assets (for example, U.S.Treasury securities), with potential knock-on effects on traditional financial markets.

Second, while stablecoins with high quality backing assets can maintain their pegs during normal times, they may still be fragile during periods of significant stress. When stablecoins lose their peg against the dollar, the effect can reverberate through the sector.

Third, smart contracts, such as the one-to-one exchange facilities backing Dai, can create interlinkages between DeFi participants. Such facilities can be created at the discretion of any individual participant and operate autonomously. Without appropriate consideration of the risks posed to the wider ecosystem, these interlinkages can channel and amplify contagion.

This paper provides a detailed account of how SVB's failure affected USDC and other stablecoins during March 2023. Our account is backed by granular data on both the primary and secondary market activities of the affected stablecoins.

Policy discussions relating to the design of stablecoin regulations are outside of the scope of our study.

Future research should explore relevant counterfactuals and other instances of pressure in stablecoin markets to better understand how the traditional and DeFi markets interact during periods of significant stress. Further studies are particularly important as stablecoins continue to expand their role in the economy.

#### 1\. The Run on SVB and its implications for USDC

On the morning of Friday, March 10, 2023, Silicon Valley Bank ("SVB") entered bank resolution after experiencing over $40 billion in withdrawals from depositors in a single day. [3](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#fn3 "footnote 3") At 10 p.m. on Friday evening, Circle announced that it was unable to withdraw $3.3 billion of USDC reserves from SVB (around 8% of total reserves at the time), sparking a wave of redemption requests for the stablecoin. [4](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#fn4 "footnote 4")

Solvency concerns around Circle are likely to have played a part. As a private company at the time, Circle was not subject to public disclosure requirements; however, subsequent filing with the Securities and Exchange Commission on April 1, 2025, stated that Circle's total stockholders' equity as of December 31, 2023, was $0.34 billion, representing just over a tenth of the $3.3 billion reserves held at SVB. [5](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#fn5 "footnote 5") [\*](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#fn50 "footnote *") Without a public guarantee on the uninsured deposits at SVB, Circle faced the possibility of a significant shortfall.

Solvency concerns can morph and extend into liquidity concerns. Redemption requests in the primary market for USDC rose sharply after the announcement that SVB was taken into receivership, ahead of Circle's public acknowledgment that it was unable to access deposits at SVB. Suspension of primary market redemptions over the ensuing weekend contributed to selling pressure on USDC in the secondary markets, triggering a depeg against the U.S. dollar in the secondary market. Public reassurances from Circle that it would "stand behind USDC and cover any shortfall using corporate resources, involving external capital if necessary," may have helped to shore up the price of USDC during the weekend, but were not sufficient to restore the peg. [6](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#fn6 "footnote 6")

**1.1 Primary Market Shutdown**

Our granular dataset allows us to analyze the market dynamics during the SVB episode in great detail. [7](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#fn7 "footnote 7") Figure 1 tracks the hourly net issuance of USDC on its primary market (bars), overlaid on top of the secondary market price of USDC (line), from Thursday, March 9 to Tuesday, March 14, 2023. Event lines indicate the timing of major public announcements related to the episode.

##### Figure 1. USDC Primary Market Net Issuance and Secondary Market Price

![Figure 1. USDC Primary Market Net Issuance and Secondary Market Price. See accessible link for data.](https://www.federalreserve.gov/econres/notes/feds-notes/fig1-3958.png)

Source: Allium, CryptoCompare.

[Accessible version](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-accessible-20251217.htm#fig1)

The bars indicate significant USDC redemptions after SVB was taken into receivership at 11:37 a.m. ET on Friday, March 10, even before Circle's public announcement around 10 p.m. that same day. Redemptions peaked shortly before this announcement, then dropped to minimal levels over the weekend, as Circle announced that issuance and redemptions were "constrained by working hours of the U.S. banking systems." [8](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#fn8 "footnote 8")

The selloffs translated into a dramatic depeg when Circle publicly tweeted about its exposure to SVB and the primary market largely ceased operations (as shown by the line). At its trough, USDC traded at 86 cents to the dollar. [9](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#fn9 "footnote 9") Public commitment from Circle, to stand behind USDC using "external capital," on Saturday, March 11 provided price support but did not restore the peg.

The "resolution weekend" for SVB culminated in a joint press release by the Department of the Treasury, the Federal Reserve Board, and the FDIC at 6:15 p.m. ET, Sunday, March 12, 2023. The press release announced that the Federal Reserve "will make available additional funding to eligible depository institutions to help assure banks have the ability to meet the needs of all their (insured and uninsured) depositors." USDC's price on the secondary market recovered sharply after the backstop announcement on Sunday and fully recovered once Circle began processing redemptions on Monday, March 13.


[... middle omitted — see footer ...]


21\. Under proposed legislation, Treasury securities held by stablecoin issuers must be short term. Therefore, stablecoin issuers will hold a specific slice of the overall Treasury market. [Return to text](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#f21)

22\. As of October 31, 2025, USDS – a rebranding of Dai – has a market capitalization of $9.1 billion (See https://www.coingecko.com/en/coins/usds). [Return to text](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#f22)

23\. Information such as timestamps, wallet addresses, and value of a given transaction is public. Different blockchains may have different protocols regarding what is publicly available. [Return to text](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#f23)

24\. We exclude from our analysis any blockchains on which USDC was not available during the time period we study. Two blog posts from Circle allow us to determine this set of blockchains: A blog post from Circle (https://www.circle.com/blog/usdc-coming-to-six-new-blockchains) on August 23, 2023 announced six new blockchains it was launching on, and lists the nine blockchains on which USDC was already issued: Algorand, Arbitrum, Avalanche, Ethereum, Flow, Hedera, Solana, Stellar, and TRON. An earlier blog post in June (https://www.circle.com/blog/usdc-on-arbitrum-now-available) announced USDC's launch on Arbitrum. Thus, we can ascertain that USDC was officially issued on Algorand, Avalanche, Ethereum, Flow, Hedera, Solana, Stellar, and TRON as of the time period we analyze. Of these eight blockchains, we include observations on Avalanche, Ethereum, Solana, and TRON. We make the assumption, due to the small amount of USDC issued on the four blockchains for which we do not have data, the primary market activity on those blockchains would not affect our overall results if we included them. In our analysis, the vast majority of activity we observe is on Ethereum or Tron. [Return to text](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#f24)

\*On January 8, 2026, a typo in this sentence was corrected to state "$0.34 billion" - as originally intended - instead of "$0.34 million". [Return to text](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html#f50)

**Please cite this note as:**

Du, Chuan, Ria Sonawane, and Cy Watsky (2025). "In the Shadow of Bank Runs: Lessons from the Silicon Valley Bank Failure and Its Impact on Stablecoins," FEDS Notes. Washington: Board of Governors of the Federal Reserve System, December 17, 2025, https://doi.org/10.17016/2380-7172.3958.

_**Disclaimer:** FEDS Notes are articles in which Board staff offer their own views and present analysis on a range of topics in economics and finance. These articles are shorter and less technically oriented than FEDS Working Papers and IFDP papers._

[Back to Top](https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html# "Scroll To Top")

Last Update:
January 08, 2026

──────── [TRUNCATED] ────────
Showing 11,953 chars (head) + 3,628 chars (tail) of 49,964 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\www.federalreserve.gov-77184a6ab4.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\www.federalreserve.gov-77184a6ab4.md" offset=92 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────