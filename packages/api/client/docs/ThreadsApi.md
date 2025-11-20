# ThreadsApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**archiveThreadApiThreadsThreadIdArchivePatch**](#archivethreadapithreadsthreadidarchivepatch) | **PATCH** /api/threads/{thread_id}/archive | Archive Thread|
|[**createMessageApiThreadsThreadIdMessagesPost**](#createmessageapithreadsthreadidmessagespost) | **POST** /api/threads/{thread_id}/messages | Create Message|
|[**createThreadApiThreadsPost**](#createthreadapithreadspost) | **POST** /api/threads | Create Thread|
|[**deleteThreadApiThreadsThreadIdDelete**](#deletethreadapithreadsthreadiddelete) | **DELETE** /api/threads/{thread_id} | Delete Thread|
|[**generateThreadTitleApiThreadsThreadIdGenerateTitlePost**](#generatethreadtitleapithreadsthreadidgeneratetitlepost) | **POST** /api/threads/{thread_id}/generate-title | Generate Thread Title|
|[**getMessagesApiThreadsThreadIdMessagesGet**](#getmessagesapithreadsthreadidmessagesget) | **GET** /api/threads/{thread_id}/messages | Get Messages|
|[**getThreadApiThreadsThreadIdGet**](#getthreadapithreadsthreadidget) | **GET** /api/threads/{thread_id} | Get Thread|
|[**listThreadsApiThreadsGet**](#listthreadsapithreadsget) | **GET** /api/threads | List Threads|
|[**unarchiveThreadApiThreadsThreadIdUnarchivePatch**](#unarchivethreadapithreadsthreadidunarchivepatch) | **PATCH** /api/threads/{thread_id}/unarchive | Unarchive Thread|
|[**updateThreadTitleApiThreadsThreadIdTitlePatch**](#updatethreadtitleapithreadsthreadidtitlepatch) | **PATCH** /api/threads/{thread_id}/title | Update Thread Title|

# **archiveThreadApiThreadsThreadIdArchivePatch**
> ThreadResponse archiveThreadApiThreadsThreadIdArchivePatch()

Archive a thread.  Args:     thread_id: Thread UUID     current_user: The authenticated user     thread_repository: The thread repository instance from dependency injection  Returns:     ThreadResponse: The archived thread  Raises:     HTTPException: If thread not found or an error occurs

### Example

```typescript
import {
    ThreadsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ThreadsApi(configuration);

let threadId: string; // (default to undefined)

const { status, data } = await apiInstance.archiveThreadApiThreadsThreadIdArchivePatch(
    threadId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **threadId** | [**string**] |  | defaults to undefined|


### Return type

**ThreadResponse**

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

# **createMessageApiThreadsThreadIdMessagesPost**
> MessageResponse createMessageApiThreadsThreadIdMessagesPost(createMessageRequest)

Create a new message in a thread.  Args:     thread_id: Thread UUID     request: Request containing message data     current_user: The authenticated user     thread_repository: The thread repository instance from dependency injection  Returns:     MessageResponse: The created message  Raises:     HTTPException: If thread not found or an error occurs

### Example

```typescript
import {
    ThreadsApi,
    Configuration,
    CreateMessageRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ThreadsApi(configuration);

let threadId: string; // (default to undefined)
let createMessageRequest: CreateMessageRequest; //

const { status, data } = await apiInstance.createMessageApiThreadsThreadIdMessagesPost(
    threadId,
    createMessageRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **createMessageRequest** | **CreateMessageRequest**|  | |
| **threadId** | [**string**] |  | defaults to undefined|


### Return type

**MessageResponse**

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

# **createThreadApiThreadsPost**
> ThreadResponse createThreadApiThreadsPost(createThreadRequest)

Create a new thread.  Args:     request: Request containing optional thread ID and title     current_user: The authenticated user     thread_repository: The thread repository instance from dependency injection  Returns:     ThreadResponse: The created thread  Raises:     HTTPException: If an error occurs creating the thread

### Example

```typescript
import {
    ThreadsApi,
    Configuration,
    CreateThreadRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ThreadsApi(configuration);

let createThreadRequest: CreateThreadRequest; //

const { status, data } = await apiInstance.createThreadApiThreadsPost(
    createThreadRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **createThreadRequest** | **CreateThreadRequest**|  | |


### Return type

**ThreadResponse**

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

# **deleteThreadApiThreadsThreadIdDelete**
> deleteThreadApiThreadsThreadIdDelete()

Delete a thread and all its messages.  Args:     thread_id: Thread UUID     current_user: The authenticated user     thread_repository: The thread repository instance from dependency injection  Raises:     HTTPException: If thread not found or an error occurs

### Example

```typescript
import {
    ThreadsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ThreadsApi(configuration);

let threadId: string; // (default to undefined)

const { status, data } = await apiInstance.deleteThreadApiThreadsThreadIdDelete(
    threadId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **threadId** | [**string**] |  | defaults to undefined|


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

# **generateThreadTitleApiThreadsThreadIdGenerateTitlePost**
> any generateThreadTitleApiThreadsThreadIdGenerateTitlePost(generateTitleRequest)

Generate a title for a thread using AI based on messages.  Returns an SSE stream with the generated title for assistant-ui compatibility.  Args:     thread_id: Thread UUID     request: Request containing messages to generate title from     current_user: The authenticated user     thread_repository: The thread repository instance from dependency injection  Returns:     StreamingResponse: SSE stream with generated title  Raises:     HTTPException: If thread not found or an error occurs

### Example

```typescript
import {
    ThreadsApi,
    Configuration,
    GenerateTitleRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ThreadsApi(configuration);

let threadId: string; // (default to undefined)
let generateTitleRequest: GenerateTitleRequest; //

const { status, data } = await apiInstance.generateThreadTitleApiThreadsThreadIdGenerateTitlePost(
    threadId,
    generateTitleRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **generateTitleRequest** | **GenerateTitleRequest**|  | |
| **threadId** | [**string**] |  | defaults to undefined|


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

# **getMessagesApiThreadsThreadIdMessagesGet**
> MessageListResponse getMessagesApiThreadsThreadIdMessagesGet()

Get all messages for a thread.  Args:     thread_id: Thread UUID     current_user: The authenticated user     thread_repository: The thread repository instance from dependency injection  Returns:     MessageListResponse: List of messages ordered by created_at  Raises:     HTTPException: If thread not found or an error occurs

### Example

```typescript
import {
    ThreadsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ThreadsApi(configuration);

let threadId: string; // (default to undefined)

const { status, data } = await apiInstance.getMessagesApiThreadsThreadIdMessagesGet(
    threadId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **threadId** | [**string**] |  | defaults to undefined|


### Return type

**MessageListResponse**

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

# **getThreadApiThreadsThreadIdGet**
> ThreadResponse getThreadApiThreadsThreadIdGet()

Get a specific thread.  Args:     thread_id: Thread UUID     current_user: The authenticated user     thread_repository: The thread repository instance from dependency injection  Returns:     ThreadResponse: The thread  Raises:     HTTPException: If thread not found or an error occurs

### Example

```typescript
import {
    ThreadsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ThreadsApi(configuration);

let threadId: string; // (default to undefined)

const { status, data } = await apiInstance.getThreadApiThreadsThreadIdGet(
    threadId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **threadId** | [**string**] |  | defaults to undefined|


### Return type

**ThreadResponse**

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

# **listThreadsApiThreadsGet**
> ThreadListResponse listThreadsApiThreadsGet()

List all threads for the current user.  Args:     include_archived: Whether to include archived threads (default: True)     current_user: The authenticated user     thread_repository: The thread repository instance from dependency injection  Returns:     ThreadListResponse: List of threads  Raises:     HTTPException: If an error occurs retrieving threads

### Example

```typescript
import {
    ThreadsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ThreadsApi(configuration);

let includeArchived: boolean; // (optional) (default to true)

const { status, data } = await apiInstance.listThreadsApiThreadsGet(
    includeArchived
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **includeArchived** | [**boolean**] |  | (optional) defaults to true|


### Return type

**ThreadListResponse**

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

# **unarchiveThreadApiThreadsThreadIdUnarchivePatch**
> ThreadResponse unarchiveThreadApiThreadsThreadIdUnarchivePatch()

Unarchive a thread.  Args:     thread_id: Thread UUID     current_user: The authenticated user     thread_repository: The thread repository instance from dependency injection  Returns:     ThreadResponse: The unarchived thread  Raises:     HTTPException: If thread not found or an error occurs

### Example

```typescript
import {
    ThreadsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ThreadsApi(configuration);

let threadId: string; // (default to undefined)

const { status, data } = await apiInstance.unarchiveThreadApiThreadsThreadIdUnarchivePatch(
    threadId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **threadId** | [**string**] |  | defaults to undefined|


### Return type

**ThreadResponse**

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

# **updateThreadTitleApiThreadsThreadIdTitlePatch**
> ThreadResponse updateThreadTitleApiThreadsThreadIdTitlePatch(updateThreadTitleRequest)

Update a thread\'s title.  Args:     thread_id: Thread UUID     request: Request containing new title     current_user: The authenticated user     thread_repository: The thread repository instance from dependency injection  Returns:     ThreadResponse: The updated thread  Raises:     HTTPException: If thread not found or an error occurs

### Example

```typescript
import {
    ThreadsApi,
    Configuration,
    UpdateThreadTitleRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ThreadsApi(configuration);

let threadId: string; // (default to undefined)
let updateThreadTitleRequest: UpdateThreadTitleRequest; //

const { status, data } = await apiInstance.updateThreadTitleApiThreadsThreadIdTitlePatch(
    threadId,
    updateThreadTitleRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **updateThreadTitleRequest** | **UpdateThreadTitleRequest**|  | |
| **threadId** | [**string**] |  | defaults to undefined|


### Return type

**ThreadResponse**

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

