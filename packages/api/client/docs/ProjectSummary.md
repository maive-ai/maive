# ProjectSummary

AI-generated project summary with structured information.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**summary** | **string** | Brief one-sentence summary of the project status | [default to undefined]
**recent_actions** | **Array&lt;string&gt;** | List of recent actions taken on the project (2-3 bullet points) | [optional] [default to undefined]
**next_steps** | **Array&lt;string&gt;** | List of recommended next steps (2-3 bullet points) | [optional] [default to undefined]

## Example

```typescript
import { ProjectSummary } from './api';

const instance: ProjectSummary = {
    summary,
    recent_actions,
    next_steps,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
