# MessageListResponse

Response model for list of messages.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**messages** | [**Array&lt;MessageResponse&gt;**](MessageResponse.md) | List of messages | [default to undefined]
**total** | **number** | Total number of messages | [default to undefined]

## Example

```typescript
import { MessageListResponse } from './api';

const instance: MessageListResponse = {
    messages,
    total,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
