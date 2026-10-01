# Research Hypothesis Register

Create the initial record before running any experiment. Predeclare data,
parameter family and chronological research/validation/OOS periods. Record every
attempt, including negative findings; do not select only favorable results.

```yaml
hypothesis_id: null
revision: null
created_at: null
question: null
economic_behavioral_rationale: null
data_required: null
parameter_family: null
research_period: null
validation_period: null
oos_period: null
result: null
decision: null
notes: null
```

No registered hypotheses yet. The database maps the rationale to
`economic_rationale`, period pairs to start/end dates, and records revisions in
`recorded_at`. Append result revisions instead of rewriting earlier registration.
Record code/config/input versions with evidence. Repeated final-OOS inspection
can invalidate its holdout role even when no automatic optimization is used.
