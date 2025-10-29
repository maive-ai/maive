# ChatApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**streamRoofingChatApiChatRoofingPost**](#streamroofingchatapichatroofingpost) | **POST** /api/chat/roofing | Stream Roofing Chat|

# **streamRoofingChatApiChatRoofingPost**
> any streamRoofingChatApiChatRoofingPost(chatRequest)

Stream roofing chat responses via Server-Sent Events.  Args:     request: Chat request with message history     current_user: Authenticated user (from JWT)     chat_service: Chat service dependency  Returns:     StreamingResponse: SSE stream of chat responses

### Example

```typescript
import {
    ChatApi,
    Configuration,
    ChatRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ChatApi(configuration);

let chatRequest: ChatRequest; //

const { status, data } = await apiInstance.streamRoofingChatApiChatRoofingPost(
    chatRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **chatRequest** | **ChatRequest**|  | |


### Return type

**any**

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

