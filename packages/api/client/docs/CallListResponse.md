# CallListResponse

Response model for the complete call list.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**items** | [**Array&lt;CallListItemResponse&gt;**](CallListItemResponse.md) | List of call list items | [default to undefined]
**total** | **number** | Total number of items in the call list | [default to undefined]

## Example

```typescript
import { CallListResponse } from './api';

const instance: CallListResponse = {
    items,
    total,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
