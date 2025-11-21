# TwilioApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**getTokenApiVoiceAiTwilioTokenGet**](#gettokenapivoiceaitwiliotokenget) | **GET** /api/voice-ai/twilio/token | Get Token|

# **getTokenApiVoiceAiTwilioTokenGet**
> { [key: string]: string | null; } getTokenApiVoiceAiTwilioTokenGet()

Generate Twilio Access Token for browser calling.

### Example

```typescript
import {
    TwilioApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new TwilioApi(configuration);

const { status, data } = await apiInstance.getTokenApiVoiceAiTwilioTokenGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**{ [key: string]: string | null; }**

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

