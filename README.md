# How well do the job-skill tags hold up?

## How I checked

I reviewed all 50 job descriptions against the supplied skill list. I counted a
tag as right only when the description supports it and it matches a listed
skill. I accepted these wording variants: Financial Modeling/Modelling,
Node/Node.js, Postgres/PostgreSQL, Excel/Microsoft Excel, JS/JavaScript, and
ML/Machine Learning. I did not treat the role title by itself as evidence, or
stretch a partial match: “API” is not “REST APIs”, and “Social Media” is not
the more specific “Social Media Marketing”.

A skill described as needed, required, or something the person will use counts
as required. A skill introduced as a bonus, “nice to have”, or a plus counts as
optional. Optional tags can be right, but leaving an optional skill out is not
a miss. If the same skill appears as both required and optional, I count it as
required.

## Results

There are 200 model tags: **170 right and 30 wrong**, so **85.0% of the tags
were right (170/200)**. Of the right tags, 150 matched required skills and 20
matched optional ones.

Across the descriptions, I found **177 required skill mentions**. The model
tagged 150 and missed 27: a **15.3% miss rate (27/177)**, or **84.7% coverage**.
These are tag-level totals across all 50 descriptions, not the share of jobs
with every tag correct.

## Three patterns in the errors

1. **Tags outside the supplied skill list (18).** For example: Teamwork
   (`JD001`), API (`JD023`), and Social Media (`JD045`).
2. **Listed skills with no support in that description (12).** For example:
   SAP (`JD004`), Kubernetes (`JD007`), and Blockchain (`JD018`). A skill being
   in the inventory does not make it relevant to every job.
3. **Required skills left out (27).** For example: Interviewing and HR
   Operations (`JD010`), PostgreSQL and REST APIs (`JD043`), and Copywriting
   (`JD045`).

## What I would change first

I would make the tagger return a short supporting quote and say whether each
skill is required or optional. That gives a reviewer something concrete to
check and makes unsupported tags easier to catch. I would test the change on a
new, manually labeled set, using the same rules, then compare tag precision
and required-skill coverage with these results. The fix is useful only if it
cuts unsupported tags without causing more required skills to be missed.

## Files and tool use

`labels.csv` shows the right required tags, right optional tags, wrong tags,
and missing required skills for each job. Run `python evaluate_tags.py` in this
folder to regenerate the labels and metrics. Run
`python -m unittest discover -s . -p "test_*.py"` for the tests.

Copilot helped write the evaluator and edit this summary. I checked the rules,
examples, and totals against the supplied files. The code and tests are
included so the results can be reproduced.
