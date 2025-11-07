### Labeling
- Labels are list of deviation instances
    [[(class_name, start_time), (class_name, start_time)], [(class_name, start_time), (class_name, start_time)]]
    - first nested list is for the first rilla call, second is for the next rilla call
- Start time is defined as the start time of the sentence where the deviation is explicitly mentioned, where start time is a timestamp (HH:MM:SS) from the start of the recording

#### Deviation Definition
- Something mentioned during the call that isn't tracked in either the recording OR estimate
-- If it's in the form but not the estimate, should we track it? -- probably not


### NOT a Deviation
- Shingle color that's agreed upon but not specified in the estimate. It seems like they track that in Notes in Production. It seems like they're the same price so it's not a problem.