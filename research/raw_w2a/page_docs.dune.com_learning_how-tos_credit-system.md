> ## Documentation Index
>
> Fetch the complete documentation index at: [/llms.txt](https://docs.dune.com/llms.txt)
>
> Use this file to discover all available pages before exploring further.

[Skip to main content](https://docs.dune.com/learning/how-tos/credit-system#content-area)

# [​](https://docs.dune.com/learning/how-tos/credit-system\#how-you-spend-credits-on-dune)  How you spend credits on Dune

Dune uses a usage-based credit system that charges based on actual compute resources consumed, ensuring fair pricing for all users regardless of query complexity.See full blog post announcement [here](https://dune.com/blog/credits-changing)

## [​](https://docs.dune.com/learning/how-tos/credit-system\#how-the-credit-system-works)  How the Credit System Works

Our query engine uses a flexible credit-based pricing model that scales with your actual resource consumption. When you run a query, credits are spent in proportion to the resources used—simple queries cost fewer credits, while complex queries that require more computational resources use more credits.This approach ensures fair pricing across our platform, which spans 100+ chains, complex tables, and multiple ways to consume data through APIs and various connector options. The credit system adapts to your needs: small, efficient queries are economical, while larger, more complex queries can leverage extended timeouts and additional resources as needed.Your credits work seamlessly across all query types and data consumption methods, providing transparent and predictable pricing that scales with your usage.**Key benefits:**

- **Usage-based** – Pay in proportion to actual consumption
- **Efficiency** – Incentives to write cleaner, optimized queries
- **Scalable** – Sustainable future support for larger workloads with longer timeouts and expanded connector options to come in the near future

This fair, usage-based model ensures Dune can keep pace with your most ambitious data needs.

## [​](https://docs.dune.com/learning/how-tos/credit-system\#credit-pricing)  Credit Pricing

Credits are consumed based on the actual compute resources used for each query execution. The more complex your query, the more credits it consumes, but simple queries cost significantly less. At the moment, we don’t share a single, per-query formula because credit usage depends on real-time factors (the compute your query actually uses, the engine you choose, and current network/data access conditions.To stay in full control, you can set:

- a global query cost cap (per-execution ceiling). More info on how to do this [here](https://app.arcade.software/share/C60r4u7ESOp5RXRuzbSN).
- a monthly extra credit limit (account-level ceiling).
These controls ensure you never exceed what you’re comfortable spending per run or per month. Learn how to set this up [here](https://app.arcade.software/share/so8QGM4H4MU0OWRWhNe9).

**Credit Pricing = Extra Credit Pricing**

On paid plans, additional usage is billed at the plan’s extra credit rate, up to your configured extra credit limit. Free accounts and free trials cannot buy extra credits.**Quick Plan Reference**

| Plan | Monthly Price | Annual Price | Credits/Month | Cost per 100 Credits |
| --- | --- | --- | --- | --- |
| **Free (view-only)** | Free | - | 0 | Not available |
| **Analyst** | $75/month | - | 4,000 | $1.875 |
| **Analyst (Annual)** | $65/month billed annually | $780/year | 4,000 | $1.625 |
| **Plus** | $399/month | - | 25,000 | $1.596 |
| **Plus (Annual)** | $349/month billed annually | $4,188/year | 25,000 | $1.396 |
| **Legacy Premium** | No longer available | - | Varies | [Contact support](mailto:support@dune.com) |
| **Enterprise** | Favorable Custom Pricing | - | Custom | **Favorable rates** \- [Contact sales](https://dune.com/enterprise) |

**Save with Enterprise Pricing**: Enterprise plans receive **significantly lower per-credit rates** compared to standard plans, plus customized support and tailored solutions. Whether you’re scaling up or just getting started, [contact our sales team](https://dune.com/enterprise) to discuss custom pricing that fits your needs.

**Legacy Premium**: This plan is no longer available for new subscriptions. Existing Premium customers can continue to use their plan.

Explore the complete pricing plan with credit limits and features for each tier: [dune.com/pricing](https://dune.com/pricing)


[... middle omitted — see footer ...]


How can I monitor my credit consumption?

The usage and billing dashboard shows credits used, extra credits, and historical usage.

Will I see the cost before running a query?

You’ll see costs after execution.

Can I run bigger queries now?

Yes more complex queries and higher data volumes with longer timeouts for Enterprise clients.

What is a system user? Is that for scheduled jobs?

Yes, the system user represents automated executions on the Dune platform. This includes scheduled query runs, materialized view refreshes, and other background jobs that run without direct user interaction. When you see credit usage attributed to a system user, it typically means those credits were consumed by your scheduled queries or automated data refresh processes rather than manual query executions.

### [​](https://docs.dune.com/learning/how-tos/credit-system\#optimization-&-support)  Optimization & Support

How can I lower my credit usage?

Write efficient SQL, limit unnecessary joins or scans, and reuse results when possible. Our docs include [query optimization tips](https://docs.dune.com/query-engine/writing-efficient-queries).

What if I consistently exceed my plan credits?

You can upgrade to a higher plan or contact our sales team to discuss a custom Enterprise solution.

Who do I contact for help?

Reach out to [support@dune.com](mailto:support@dune.com) or your Dune account manager for Enterprise plans.

Was this page helpful?

YesNo

──────── [TRUNCATED] ────────
Showing 4,386 chars (head) + 1,456 chars (tail) of 9,425 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\docs.dune.com-39adcfa5a7.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\docs.dune.com-39adcfa5a7.md" offset=51 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────