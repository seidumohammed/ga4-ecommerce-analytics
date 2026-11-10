# AI-assisted delivery

This project was built with an AI coding assistant. This note says what the assistant was used for, what stayed a human
decision, and which checks stop its mistakes from reaching the numbers. It is written to be reused on other projects.

## How the work was organised

1. **Brief first.** Before any code, the questions, the metric definitions and the data problems to expect were written down
   (see [business-brief.md](business-brief.md)). A clear brief is what makes AI help useful, because the assistant can then
   be asked for a specific model instead of a vague one.
2. **Small, specific requests.** Each request named one model or one test, its inputs, its grain and the rule to apply,
   for example "one row per session, source from the first events, engaged after 10 seconds, 2 page views or a purchase".
3. **Tests as guardrails.** Every model got tests before it was trusted: keys, accepted values, reconciliation to other
   tables, and unit tests for the business rules.
4. **A known answer to check against.** The synthetic data comes with a manifest of the problems planted in it. The
   pipeline has to find exactly those, which tests the cleaning logic against something the assistant did not write itself
   in the same step.
5. **Every failure read, not patched.** When a test failed, the first question was whether the code or the test was
   wrong, and the answer was written down.

## What the assistant did

- Drafted SQL for models, macros and tests, and the generator that produces the data.
- Suggested edge cases (late events, double-fired tags, consent-denied sessions, midnight-crossing sessions).
- Wrote first drafts of documentation, which were then checked line by line against the warehouse.
- Built the dashboard page.

## What stayed a human decision

- Metric definitions, such as what counts as a valid session or an order, and which rows to exclude.
- Which problems to plant and how many.
- Whether a failing test meant a bug or a wrong expectation.
- Every number that appears in a document. Each one was queried from the gold tables before it was written.
- What to publish, and what to say about limits.

## Examples where the checks mattered

| What happened | How it was caught | Decision |
|---|---|---|
| Spend in the channel table came from whole weeks, but revenue came from the selected days, so return on ad spend looked far too low for a short range | Comparing a filtered dashboard view with a direct warehouse query | Added a daily spend table and used it for the exact date range |
| Daily revenue in two tables differed on 7 days | A reconciliation test failed | It was a real definition difference (purchase time against session start for sessions that cross midnight). Both were kept, documented, and a test proves it is the only cause |
| The generator picked "missing" ad-spend days from the wrong date range on short runs | The planted-problem test found 1 missing day when 2 were planted | Fixed the generator |
| The first engagement rate was 90% | Reading the output against what a real shop sees (roughly 50 to 65%) | Changed how the generator makes page views and engagement time |
| Email return on ad spend came out at 91 times | Same review | Corrected the cost assumption in the synthetic spend |
| The lineage site embedded local file paths in its compiled SQL | A search of the file before publishing | Rebuilt the docs with a generic path |

## A short checklist for AI-assisted analytics work

- Write the question and the metric definition before asking for code.
- Ask for one small piece at a time, with its grain and inputs.
- Add tests before relying on the output, and include reconciliation between tables.
- Break a rule on purpose and confirm a test fails.
- Query every number you publish from the data. Do not copy numbers from a draft.
- Search for personal data, paths and credentials in anything you publish.
- Record decisions and limits next to the work.

## What this does not claim

The assistant is a tool, and it makes mistakes, including in the examples above. This project does not use an automated
agent that acts on its own. The process above is a way of working with an assistant in the loop and a person approving
each step.
