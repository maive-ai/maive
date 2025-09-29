# ProjectStatusListResponse

Response model for multiple project statuses.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**projects** | [**Array&lt;ProjectStatusResponse&gt;**](ProjectStatusResponse.md) | List of project statuses | [default to undefined]
**total_count** | **number** | Total number of projects | [default to undefined]
**provider** | [**CRMProvider**](CRMProvider.md) | CRM provider | [default to undefined]

## Example

```typescript
import { ProjectStatusListResponse } from './api';

const instance: ProjectStatusListResponse = {
    projects,
    total_count,
    provider,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
