# Development checkpoint history

This branch now contains the complete frozen study and held-out results. See the
[current publication and verification guide](frozen-study-release.md).

The amended development checkpoint is preserved at commit
`824ec954444e7cc990d09f99cc9062b4874599b2`. It contained all 432 development trials
and deliberately withheld the reserved dataset and original generator. Those
inputs are now released after completion of the held-out evaluation. Its original
publication manifest is retained in
[the history archive](../public_checkpoint/history/2026-11-13-development.json).

The preliminary 144-trial checkpoint remains at commit
`8beb10e95f852d6a6ee7f0cbd9c08e36f1040019`. Neither checkpoint nor the original pilot
on `main` has been rewritten. Original development evidence remains unchanged.

The [amended development review](followup-amended-development-review.md) records
the earlier findings: 54/108 authorized successes for instructions only and
102/108 for each gated arm, with no observed recovery advantage. Those results
remain separate from the held-out findings. Historical status statements in that
review describe the pre-freeze stage at which it was written.
