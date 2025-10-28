# CallListApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**addToCallListApiCallListAddPost**](#addtocalllistapicalllistaddpost) | **POST** /api/call-list/add | Add To Call List|
|[**clearCallListApiCallListDelete**](#clearcalllistapicalllistdelete) | **DELETE** /api/call-list | Clear Call List|
|[**getCallListApiCallListGet**](#getcalllistapicalllistget) | **GET** /api/call-list | Get Call List|
|[**markCallCompletedApiCallListProjectIdCompletedPatch**](#markcallcompletedapicalllistprojectidcompletedpatch) | **PATCH** /api/call-list/{project_id}/completed | Mark Call Completed|
|[**removeFromCallListApiCallListProjectIdDelete**](#removefromcalllistapicalllistprojectiddelete) | **DELETE** /api/call-list/{project_id} | Remove From Call List|

# **addToCallListApiCallListAddPost**
> CallListResponse addToCallListApiCallListAddPost(addToCallListRequest)

Add projects to the user\'s call list.  Adds multiple projects to the authenticated user\'s call list. Duplicate projects are silently ignored.  Args:     request: Request containing list of project IDs to add     current_user: The authenticated user     call_list_repository: The call list repository instance from dependency injection  Returns:     CallListResponse: The updated call list  Raises:     HTTPException: If an error occurs adding projects

### Example

```typescript
import {
    CallListApi,
    Configuration,
    AddToCallListRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new CallListApi(configuration);

let addToCallListRequest: AddToCallListRequest; //

const { status, data } = await apiInstance.addToCallListApiCallListAddPost(
    addToCallListRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **addToCallListRequest** | **AddToCallListRequest**|  | |


### Return type

**CallListResponse**

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

# **clearCallListApiCallListDelete**
> clearCallListApiCallListDelete()

Clear all items from the user\'s call list.  Args:     current_user: The authenticated user     call_list_repository: The call list repository instance from dependency injection  Raises:     HTTPException: If an error occurs clearing the call list

### Example

```typescript
import {
    CallListApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CallListApi(configuration);

const { status, data } = await apiInstance.clearCallListApiCallListDelete();
```

### Parameters
This endpoint does not have any parameters.


### Return type

void (empty response body)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**204** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getCallListApiCallListGet**
> CallListResponse getCallListApiCallListGet()

Get the user\'s call list.  Returns all items in the authenticated user\'s call list, ordered by position.  Args:     current_user: The authenticated user     call_list_repository: The call list repository instance from dependency injection  Returns:     CallListResponse: The user\'s call list  Raises:     HTTPException: If an error occurs retrieving the call list

### Example

```typescript
import {
    CallListApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CallListApi(configuration);

const { status, data } = await apiInstance.getCallListApiCallListGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**CallListResponse**

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

# **markCallCompletedApiCallListProjectIdCompletedPatch**
> CallListItemResponse markCallCompletedApiCallListProjectIdCompletedPatch(markCallCompletedRequest)

Mark a call as completed or not completed.  Args:     project_id: The project ID to update     request: Request containing completion status     current_user: The authenticated user     call_list_repository: The call list repository instance from dependency injection  Returns:     CallListItemResponse: The updated call list item  Raises:     HTTPException: If the project is not found or an error occurs

### Example

```typescript
import {
    CallListApi,
    Configuration,
    MarkCallCompletedRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new CallListApi(configuration);

let projectId: string; // (default to undefined)
let markCallCompletedRequest: MarkCallCompletedRequest; //

const { status, data } = await apiInstance.markCallCompletedApiCallListProjectIdCompletedPatch(
    projectId,
    markCallCompletedRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **markCallCompletedRequest** | **MarkCallCompletedRequest**|  | |
| **projectId** | [**string**] |  | defaults to undefined|


### Return type

**CallListItemResponse**

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

# **removeFromCallListApiCallListProjectIdDelete**
> removeFromCallListApiCallListProjectIdDelete()

Remove a project from the user\'s call list.  Args:     project_id: The project ID to remove     current_user: The authenticated user     call_list_repository: The call list repository instance from dependency injection  Raises:     HTTPException: If the project is not found or an error occurs

### Example

```typescript
import {
    CallListApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CallListApi(configuration);

let projectId: string; // (default to undefined)

const { status, data } = await apiInstance.removeFromCallListApiCallListProjectIdDelete(
    projectId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **projectId** | [**string**] |  | defaults to undefined|


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

