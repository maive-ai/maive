# CallListItemResponse

Response model for a single call list item.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **number** | Database ID of the call list item | [default to undefined]
**user_id** | **string** | Cognito user ID | [default to undefined]
**project_id** | **string** | Project/Job ID from CRM | [default to undefined]
**call_completed** | **boolean** | Whether the call has been completed | [default to undefined]
**position** | **number** | Position in the call list for ordering | [default to undefined]
**created_at** | **string** | When the item was added to the list | [default to undefined]
**updated_at** | **string** | When the item was last updated | [default to undefined]

## Example

```typescript
import { CallListItemResponse } from './api';

const instance: CallListItemResponse = {
    id,
    user_id,
    project_id,
    call_completed,
    position,
    created_at,
    updated_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
