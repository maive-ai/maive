# MessageResponse

Response model for a single message.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | Message UUID | [default to undefined]
**thread_id** | **string** | Thread UUID | [default to undefined]
**role** | **string** | Message role | [default to undefined]
**content** | **{ [key: string]: any; }** | Message content | [default to undefined]
**created_at** | **string** | When the message was created | [default to undefined]

## Example

```typescript
import { MessageResponse } from './api';

const instance: MessageResponse = {
    id,
    thread_id,
    role,
    content,
    created_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
