# JobList

Universal job list response with pagination.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**jobs** | [**Array&lt;Job&gt;**](Job.md) | List of jobs | [default to undefined]
**total_count** | **number** | Total number of jobs | [default to undefined]
**provider** | [**CRMProvider**](CRMProvider.md) | CRM provider name | [default to undefined]
**page** | **number** |  | [optional] [default to undefined]
**page_size** | **number** |  | [optional] [default to undefined]
**has_more** | **boolean** |  | [optional] [default to undefined]

## Example

```typescript
import { JobList } from './api';

const instance: JobList = {
    jobs,
    total_count,
    provider,
    page,
    page_size,
    has_more,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
