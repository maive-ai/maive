# RequiredActions

Provider-agnostic required actions from claim status calls.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**documents_needed** | [**Array&lt;DocumentNeeded&gt;**](DocumentNeeded.md) | List of required documents | [optional] [default to undefined]
**submission_method** | **string** |  | [optional] [default to undefined]
**next_steps** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { RequiredActions } from './api';

const instance: RequiredActions = {
    documents_needed,
    submission_method,
    next_steps,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
