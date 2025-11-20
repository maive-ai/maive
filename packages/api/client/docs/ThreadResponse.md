# ThreadResponse

Response model for a single thread.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | Thread UUID | [default to undefined]
**user_id** | **string** | Cognito user ID | [default to undefined]
**title** | **string** | Thread title | [default to undefined]
**archived** | **boolean** | Whether thread is archived | [default to undefined]
**created_at** | **string** | When the thread was created | [default to undefined]
**updated_at** | **string** | When the thread was last updated | [default to undefined]

## Example

```typescript
import { ThreadResponse } from './api';

const instance: ThreadResponse = {
    id,
    user_id,
    title,
    archived,
    created_at,
    updated_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
