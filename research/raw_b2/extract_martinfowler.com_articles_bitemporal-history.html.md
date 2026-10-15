# https://martinfowler.com/articles/bitemporal-history.html

# Bitemporal History

* It's often necessary to access the historical values of some property. But sometimes this history itself needs to be modified in response to retroactive updates. Bitemporal history treats time as two dimensions: actual history records what history should be given perfect transmission of information, while record history captures how our knowledge of history changes.*

07 April 2021

---

---

When we think of how some property (e.g. your address or salary) changes over time, we usually think of it as a linear sequence of changes. But surprisingly often, it can get rather more tangled than that, in a way that can often confuse computerized records.

I can illustrate all this with a simple example:

- We are handling payroll for our company. We run the payroll for our company on February 25, and our employee Sally is paid according to her monthly salary of $6000.
- On March 15 we get an apologetic letter from HR telling us that, on February 15th, Sally got a pay raise to $6500.
So what should we answer when we're asked what Sally's salary was on February 25? In one sense we should answer $6500, since we know now that that was the rate. But often we cannot ignore that on Feb 25 we thought the salary was $6000, after all that's when we ran payroll. We printed a check, sent it to her, and she cashed it. These all occurred based on the amount that her salary was. If the tax authorities asked us for her salary on Feb 25, this becomes important.

## The Two Dimensions

I find I can make sense of much of this tangle by thinking of time as two dimensions - hence the term “bitemporal”. One dimension is the actual history of Sally's salary, which I'll illustrate by sampling on the 25th of each month, since that's when payroll runs.

| date | salary |
|---|---|
| Jan 25 | 6000 |
| Feb 25 | 6500 |
| Mar 25 | 6500 |
The second dimension comes in as we ask what did we think Sally's salary history was on February 25? On February 25th we hadn't got the letter from HR, so we thought her salary was always $6000. There is a difference between the actual history, and our record of the history. We can show this by adding new dates to our table

| record date | actual date | salary |
|---|---|---|
| Jan 25 | Jan 25 | 6000 |
| Feb 25 | Jan 25 | 6000 |
| Mar 25 | Jan 25 | 6000 |
| Feb 25 | Feb 25 | 6000 |
| Mar 25 | Feb 25 | 6500 |
| Mar 25 | Mar 25 | 6500 |
I'm using the terms *actual* and *record* history for the two dimensions. You may also hear people using the terms *valid*, or *effective* (for actual) and *transaction* (for record).1

1:

The terminology of valid time and transaction time comes from [Snodgrass](https://www.amazon.com/gp/product/1558604367/ref=as_li_tl?ie=UTF8&camp=1789&creative=9325&creativeASIN=1558604367&linkCode=as2&tag=martinfowlerc-20), and is also used in the [SQL:2011](https://en.wikipedia.org/wiki/SQL:2011) standard. When I first started giving workshops about temporal modeling, back in the early naughts, I used these terms, but people found them confusing. So instead we started to use actual/record instead. Since valid/transaction hasn't become widespread usage, I'm going to follow that lesson and use actual/record here.

I read the rows of this table by saying something like “on Mar 25th, we thought Sally's salary on Feb 25th was $6500”. Using this way of thinking, I can look at the earlier table of Sally's actual history, and say that more precisely it's Sally's actual history as known (recorded) on March 25.

In programming terms, If I want to know Sally's salary, and I have no history, then I can get it with something like `sally.salary`. To add support for (actual) history I need to use `sally.salaryAt('2021-02-25')`. In a bitemporal world I need another parameter `sally.salaryAt('2021-02-25', '2021-03-25')`

Another way to visualize this is to make a plot where the x axis is actual time and the y axis is record time. I shade the region according to the salary level. (The shape of the plot is triangular since we're not trying to record future values.2)

2:

With history actual time is always at or before record time. But the notion of bitemporality can apply to the future. If I'm told on May 5 that Sally will get another increase on May 12, then I can record that increase with a record time of May 5 and an actual time of May 12.

![](bitemporal-history/intro-labels.png)

With this plot, I can make a table for how actual history changes with each run of payroll on the 25th. We see that the Feb 25 payroll ran at a time when Sally had no raise, but when the Mar 25 payroll ran, the raise was known.

![](bitemporal-history/sally-mar-25.png)

## Changing the Retroactive Change

Now consider another communication from HR

- April 5: Sorry there was an typo in our previous email. Sally's raise on Feb 15 was to $6400. Sorry for the inconvenience.
This is the kind of change that makes angels weep. But when we think of it terms of bitemporal history, it's not that difficult to understand. Here's the plot with this new bit of information.

![](bitemporal-history/sally-apr-25.png)

The horizontal lines, used for the payrols, represent the actual history at a certain point in record time. On April 25 we know Sally's salary increased from $6000 to $6400 on February 15. In that perspective, we never see Sally's $6500 salary because it was never true.

Looking at the diagram, what does a vertical line mean?

![](bitemporal-history/sally-record-history.png)

This represents our knowledge of the value at a certain date. The table indicates the recorded salary for February 25th, as our knowledge changed over time.

## Using Bitemporality

Bitemporal history is a useful way of framing history when we have to deal with retroactive changes. However we don't see it used that often, partly because many people don't know about the technique, but also because we can often get away without it.


[... middle omitted — see footer ...]


## Footnotes

### 1: Actual/record versus valid/transaction

The terminology of valid time and transaction time comes from [Snodgrass](https://www.amazon.com/gp/product/1558604367/ref=as_li_tl?ie=UTF8&camp=1789&creative=9325&creativeASIN=1558604367&linkCode=as2&tag=martinfowlerc-20), and is also used in the [SQL:2011](https://en.wikipedia.org/wiki/SQL:2011) standard. When I first started giving workshops about temporal modeling, back in the early naughts, I used these terms, but people found them confusing. So instead we started to use actual/record instead. Since valid/transaction hasn't become widespread usage, I'm going to follow that lesson and use actual/record here.

### 2: Bitemporal Future

With history actual time is always at or before record time. But the notion of bitemporality can apply to the future. If I'm told on May 5 that Sally will get another increase on May 12, then I can record that increase with a record time of May 5 and an actual time of May 12.

3: If you don't recognize this quote, you should put [Blink](https://en.wikipedia.org/wiki/Blink_(Doctor_Who)) on your watchlist. One of the finest time-travel stories ever filmed.

4: I started to explore this topic in my earlier writing on [parallel models](/eaaDev/ParallelModel.html) in the mid 2000s. I didn't continue down that path then, and I'm not sure when or if I'll revisit that trail in the future.

## Acknowledgements

Alexandre Klaser, Dave Elliman, Joshua Taylor, Martha Rohte, Mauro Vilasi, Pavlo Kerestey, Pramod Sadalge, Rebecca Parsons, Saager Mhatre, and Wolf Schlegel contributed to a useful discussion of this article on our internal mailing list.

Heikki Heinonen alerted me to some errors in the perspectives tables.

Significant Revisions
*07 April 2021:* Published

*17 March 2021:* Sent for internal review

*02 March 2021:* Started drafting

──────── [TRUNCATED] ────────
Showing 5,912 chars (head) + 1,857 chars (tail) of 20,235 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\martinfowler.com-ae6bbdb287.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\martinfowler.com-ae6bbdb287.md" offset=81 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────