# VoiceAIApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**endCallApiVoiceAiCallsCallIdDelete**](#endcallapivoiceaicallscalliddelete) | **DELETE** /api/voice-ai/calls/{call_id} | End Call|
|[**getActiveCallApiVoiceAiCallsActiveGet**](#getactivecallapivoiceaicallsactiveget) | **GET** /api/voice-ai/calls/active | Get Active Call|
|[**getCallStatusApiVoiceAiCallsCallIdGet**](#getcallstatusapivoiceaicallscallidget) | **GET** /api/voice-ai/calls/{call_id} | Get Call Status|

# **endCallApiVoiceAiCallsCallIdDelete**
> endCallApiVoiceAiCallsCallIdDelete()

End an ongoing call programmatically.  Args:     call_id: The unique identifier for the call to end     current_user: The authenticated user     voice_ai_service: The Voice AI service instance from dependency injection  Raises:     HTTPException: If the call is not found or cannot be ended

### Example

```typescript
import {
    VoiceAIApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new VoiceAIApi(configuration);

let callId: string; // (default to undefined)

const { status, data } = await apiInstance.endCallApiVoiceAiCallsCallIdDelete(
    callId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **callId** | [**string**] |  | defaults to undefined|


### Return type

void (empty response body)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**204** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getActiveCallApiVoiceAiCallsActiveGet**
> { [key: string]: any; } getActiveCallApiVoiceAiCallsActiveGet()

Get the user\'s currently active call.  Returns the active call data if one exists, otherwise returns None.  Args:     current_user: The authenticated user     call_repository: The call repository instance from dependency injection  Returns:     dict | None: The active call data or None if no active call  Raises:     HTTPException: If an error occurs retrieving the call

### Example

```typescript
import {
    VoiceAIApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new VoiceAIApi(configuration);

const { status, data } = await apiInstance.getActiveCallApiVoiceAiCallsActiveGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**{ [key: string]: any; }**

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |

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

