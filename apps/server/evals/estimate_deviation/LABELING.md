# Problem Classes

## Level 1
- Untracked product or service
    - Output
        - Description
        - Occurrences
        - Predict estimate line item directly (or hand off to specialist)
    - Business impact:
        - Cost
        - Customer experience
- Product or service tracked in form but not estimate
    - Output:
        - Description
        - Occurrences
        - Predict estimate line item directly (or hand off to specialist)
    - Business impact
        - Cost

## Level 2
- Discount applied but not tracked
    - Output:
        - Description
        - Occurrences
        - Predict estimate line item directly (or hand off to specialist)
    - Business impact
        - Cost
- Untracked or incorrect customer preference
    - Examples: color of shingles misalignment, preference for a specific type of plywood, schedule timing, communication preferences
    - Output:
        - Description
        - Occurrences
    - Business impact:
        - Customer experience
- Labor line item missing from estimate
    - Output:
        - Description
        - Occurrences
        - Predict estimate line item directly (or hand off to specialist)
    - Business impact
        - Cost

## Level 3
- Scope discrepancy
    - Examples: conversation includes the roof on a shed, but neither the cool down form nor the estimate track it
    - Output:
        - Description
        - Occurrences
    - Business impact
        - Customer experience
- Incorrect quantity
    - Examples: scope discussed during conversation or stated in cool down form appears incongruent with quantities in estimate
    - Output:
        - Description
        - Occurrences
        - Predict updated line item directly
    - Business impact
        - Cost

# Labeling

## Guidelines
- Should label all of the above issues regardless of what level implementation we're on
- Start time is defined as the start time of the sentence where the deviation is explicitly mentioned, where start time is a timestamp (HH:MM:SS) from the start of the recording

## Labeling Procedure
- Run the agent on inputs, have it pre-label it
- Review cool down form data to see if any work / scope is tracked in the cool down form but not in the estimate
- Listen to the full Rilla track, find any issues not flagged by the model, correct any errors made in pre-labeling