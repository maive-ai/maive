# TranscriptMessage

Provider-agnostic transcript message.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**role** | **string** | Speaker role: user, assistant, system | [default to undefined]
**content** | **string** | Message content | [default to undefined]
**timestamp_seconds** | **number** | Seconds from call start | [default to undefined]
**duration_seconds** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { TranscriptMessage } from './api';

const instance: TranscriptMessage = {
    role,
    content,
    timestamp_seconds,
    duration_seconds,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
