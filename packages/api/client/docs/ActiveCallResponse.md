# ActiveCallResponse

Response model for the user\'s currently active call.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**user_id** | **string** | User identifier | [default to undefined]
**call_id** | **string** | Unique call identifier | [default to undefined]
**project_id** | **string** | Associated project identifier | [default to undefined]
**status** | [**CallStatus**](CallStatus.md) | Current call status | [default to undefined]
**provider** | [**VoiceAIProvider**](VoiceAIProvider.md) | Voice AI provider | [default to undefined]
**phone_number** | **string** | Phone number being called | [default to undefined]
**listen_url** | **string** |  | [optional] [default to undefined]
**started_at** | **string** | Call start timestamp (ISO format) | [default to undefined]
**provider_data** | **any** |  | [optional] [default to undefined]

## Example

```typescript
import { ActiveCallResponse } from './api';

const instance: ActiveCallResponse = {
    user_id,
    call_id,
    project_id,
    status,
    provider,
    phone_number,
    listen_url,
    started_at,
    provider_data,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
