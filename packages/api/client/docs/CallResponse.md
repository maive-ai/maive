# CallResponse

Response model for call information.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**call_id** | **string** | Unique call identifier | [default to undefined]
**status** | [**CallStatus**](CallStatus.md) | Current call status | [default to undefined]
**provider** | [**VoiceAIProvider**](VoiceAIProvider.md) | Voice AI provider | [default to undefined]
**created_at** | **string** |  | [optional] [default to undefined]
**provider_data** | **any** |  | [optional] [default to undefined]
**analysis** | [**AnalysisData**](AnalysisData.md) |  | [optional] [default to undefined]
**messages** | [**Array&lt;TranscriptMessage&gt;**](TranscriptMessage.md) | Transcript messages from the call | [optional] [default to undefined]

## Example

```typescript
import { CallResponse } from './api';

const instance: CallResponse = {
    call_id,
    status,
    provider,
    created_at,
    provider_data,
    analysis,
    messages,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
