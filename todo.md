

"point of giving" is a PII
"key motivator that allows"

"credit score: 679" was as PIIMatch but was missed completely 
by the token step

"credit report: bad, and" was redacted

"take her" was redacted

"they were put" was redacted

"commitment is further"
"when she responds" both redacted

regex detection step is good. We can reason that the regexes are perfect the way they are in terms of matching. What we can think about is how these start and ending indices are done.

We were able to perfectly do the first page, but something happened. look into issues with the indices. It's insane how the first page is perfectly done yet the rest of the pages aren't. Is there some bad indices?



TLDR: Regexes match correctly, but something went wrong with token marking and tracking indices