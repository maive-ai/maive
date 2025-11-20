# CreateMessageRequest

Request model for creating a new message.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**message_id** | **string** | Message UUID | [default to undefined]
**role** | **string** | Message role: user, assistant, or system | [default to undefined]
**content** | **{ [key: string]: any; }** | Message content (ThreadMessage format) | [default to undefined]

## Example

```typescript
import { CreateMessageRequest } from './api';

const instance: CreateMessageRequest = {
    message_id,
    role,
    content,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
