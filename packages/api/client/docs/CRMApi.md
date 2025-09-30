# CRMApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**getAllProjectStatusesApiCrmProjectsStatusGet**](#getallprojectstatusesapicrmprojectsstatusget) | **GET** /api/crm/projects/status | Get All Project Statuses|
|[**getProjectStatusApiCrmProjectsProjectIdStatusGet**](#getprojectstatusapicrmprojectsprojectidstatusget) | **GET** /api/crm/projects/{project_id}/status | Get Project Status|

# **getAllProjectStatusesApiCrmProjectsStatusGet**
> ProjectStatusListResponse getAllProjectStatusesApiCrmProjectsStatusGet()

Get the status of all projects.  Args:     crm_service: The CRM service instance from dependency injection  Returns:     ProjectStatusListResponse: List of all project statuses  Raises:     HTTPException: If an error occurs while fetching project statuses

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

const { status, data } = await apiInstance.getAllProjectStatusesApiCrmProjectsStatusGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**ProjectStatusListResponse**

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

# **getProjectStatusApiCrmProjectsProjectIdStatusGet**
> ProjectStatusResponse getProjectStatusApiCrmProjectsProjectIdStatusGet()

Get the status of a specific project by ID.  Args:     project_id: The unique identifier for the project     crm_service: The CRM service instance from dependency injection  Returns:     ProjectStatusResponse: The project status information  Raises:     HTTPException: If the project is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let projectId: string; // (default to undefined)

const { status, data } = await apiInstance.getProjectStatusApiCrmProjectsProjectIdStatusGet(
    projectId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **projectId** | [**string**] |  | defaults to undefined|


### Return type

**ProjectStatusResponse**

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

