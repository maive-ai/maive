# VoiceAIApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**createOutboundCallApiVoiceAiCallsPost**](#createoutboundcallapivoiceaicallspost) | **POST** /api/voice-ai/calls | Create Outbound Call|
|[**getCallStatusApiVoiceAiCallsCallIdGet**](#getcallstatusapivoiceaicallscallidget) | **GET** /api/voice-ai/calls/{call_id} | Get Call Status|

# **createOutboundCallApiVoiceAiCallsPost**
> CallResponse createOutboundCallApiVoiceAiCallsPost(callRequest)

Create an outbound call.  Args:     request: The call request with phone number and context     current_user: The authenticated user     voice_ai_service: The Voice AI service instance from dependency injection  Returns:     CallResponse: The call information  Raises:     HTTPException: If call creation fails

### Example

```typescript
import {
    VoiceAIApi,
    Configuration,
    CallRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new VoiceAIApi(configuration);

let callRequest: CallRequest; //

const { status, data } = await apiInstance.createOutboundCallApiVoiceAiCallsPost(
    callRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **callRequest** | **CallRequest**|  | |


### Return type

**CallResponse**

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getCallStatusApiVoiceAiCallsCallIdGet**
> CallResponse getCallStatusApiVoiceAiCallsCallIdGet()

Get the status of a specific call by ID.  Args:     call_id: The unique identifier for the call     current_user: The authenticated user     voice_ai_service: The Voice AI service instance from dependency injection  Returns:     CallResponse: The call status information  Raises:     HTTPException: If the call is not found or an error occurs

### Example

```typescript
import {
    VoiceAIApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new VoiceAIApi(configuration);

let callId: string; // (default to undefined)

const { status, data } = await apiInstance.getCallStatusApiVoiceAiCallsCallIdGet(
    callId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **callId** | [**string**] |  | defaults to undefined|


### Return type

**CallResponse**

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

