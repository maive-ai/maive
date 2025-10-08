# CRMApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**addJobNoteApiCrmTenantJobsJobIdNotesPost**](#addjobnoteapicrmtenantjobsjobidnotespost) | **POST** /api/crm/{tenant}/jobs/{job_id}/notes | Add Job Note|
|[**createProjectApiCrmProjectsPost**](#createprojectapicrmprojectspost) | **POST** /api/crm/projects | Create Project|
|[**getAllProjectStatusesApiCrmProjectsStatusGet**](#getallprojectstatusesapicrmprojectsstatusget) | **GET** /api/crm/projects/status | Get All Project Statuses|
|[**getEstimateApiCrmTenantEstimatesEstimateIdGet**](#getestimateapicrmtenantestimatesestimateidget) | **GET** /api/crm/{tenant}/estimates/{estimate_id} | Get Estimate|
|[**getEstimateItemsApiCrmTenantEstimatesItemsGet**](#getestimateitemsapicrmtenantestimatesitemsget) | **GET** /api/crm/{tenant}/estimates/items | Get Estimate Items|
|[**getJobApiCrmTenantJobsJobIdGet**](#getjobapicrmtenantjobsjobidget) | **GET** /api/crm/{tenant}/jobs/{job_id} | Get Job|
|[**getProjectStatusApiCrmProjectsProjectIdStatusGet**](#getprojectstatusapicrmprojectsprojectidstatusget) | **GET** /api/crm/projects/{project_id}/status | Get Project Status|

# **addJobNoteApiCrmTenantJobsJobIdNotesPost**
> JobNoteResponse addJobNoteApiCrmTenantJobsJobIdNotesPost()

Add a note to a specific job.  Args:     tenant: The tenant ID     job_id: The unique identifier for the job     text: The text content of the note     pin_to_top: Whether to pin the note to the top (optional)     crm_service: The CRM service instance from dependency injection  Returns:     JobNoteResponse: The created note information  Raises:     HTTPException: If the job is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let tenant: number; // (default to undefined)
let jobId: number; // (default to undefined)
let text: string; // (default to undefined)
let pinToTop: boolean; // (optional) (default to undefined)

const { status, data } = await apiInstance.addJobNoteApiCrmTenantJobsJobIdNotesPost(
    tenant,
    jobId,
    text,
    pinToTop
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **tenant** | [**number**] |  | defaults to undefined|
| **jobId** | [**number**] |  | defaults to undefined|
| **text** | [**string**] |  | defaults to undefined|
| **pinToTop** | [**boolean**] |  | (optional) defaults to undefined|


### Return type

**JobNoteResponse**

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

# **createProjectApiCrmProjectsPost**
> any createProjectApiCrmProjectsPost(projectData)

Create a new demo project (Mock CRM only).  This endpoint is only available when using the Mock CRM provider and is intended for demo and testing purposes only.  Note: The `id`, `tenant`, and `job_id` fields in the request will be auto-generated and any provided values will be ignored.  Args:     project_data: The project data (ProjectData model)     crm_service: The CRM service instance from dependency injection  Raises:     HTTPException: If the provider doesn\'t support project creation or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration,
    ProjectData
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let projectData: ProjectData; //

const { status, data } = await apiInstance.createProjectApiCrmProjectsPost(
    projectData
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **projectData** | **ProjectData**|  | |


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
|**201** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

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

# **getEstimateApiCrmTenantEstimatesEstimateIdGet**
> EstimateResponse getEstimateApiCrmTenantEstimatesEstimateIdGet()

Get a specific estimate by ID.  Args:     tenant: The tenant ID     estimate_id: The unique identifier for the estimate     crm_service: The CRM service instance from dependency injection  Returns:     EstimateResponse: The estimate information  Raises:     HTTPException: If the estimate is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let tenant: number; // (default to undefined)
let estimateId: number; // (default to undefined)

const { status, data } = await apiInstance.getEstimateApiCrmTenantEstimatesEstimateIdGet(
    tenant,
    estimateId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **tenant** | [**number**] |  | defaults to undefined|
| **estimateId** | [**number**] |  | defaults to undefined|


### Return type

**EstimateResponse**

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

# **getEstimateItemsApiCrmTenantEstimatesItemsGet**
> EstimateItemsResponse getEstimateItemsApiCrmTenantEstimatesItemsGet()

Get estimate items with optional filters.  Args:     tenant: The tenant ID     estimate_id: Optional estimate ID to filter items     ids: Optional comma-separated string of item IDs (max 50)     active: Optional active status filter (True, False, Any)     page: Optional page number for pagination     page_size: Optional page size for pagination (max 50)     crm_service: The CRM service instance from dependency injection  Returns:     EstimateItemsResponse: The paginated list of estimate items  Raises:     HTTPException: If an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let tenant: number; // (default to undefined)
let estimateId: number; // (optional) (default to undefined)
let ids: string; // (optional) (default to undefined)
let active: string; // (optional) (default to undefined)
let page: number; // (optional) (default to undefined)
let pageSize: number; // (optional) (default to undefined)

const { status, data } = await apiInstance.getEstimateItemsApiCrmTenantEstimatesItemsGet(
    tenant,
    estimateId,
    ids,
    active,
    page,
    pageSize
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **tenant** | [**number**] |  | defaults to undefined|
| **estimateId** | [**number**] |  | (optional) defaults to undefined|
| **ids** | [**string**] |  | (optional) defaults to undefined|
| **active** | [**string**] |  | (optional) defaults to undefined|
| **page** | [**number**] |  | (optional) defaults to undefined|
| **pageSize** | [**number**] |  | (optional) defaults to undefined|


### Return type

**EstimateItemsResponse**

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

# **getJobApiCrmTenantJobsJobIdGet**
> JobResponse getJobApiCrmTenantJobsJobIdGet()

Get a specific job by ID.  Args:     tenant: The tenant ID     job_id: The unique identifier for the job     crm_service: The CRM service instance from dependency injection  Returns:     JobResponse: The job information  Raises:     HTTPException: If the job is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let tenant: number; // (default to undefined)
let jobId: number; // (default to undefined)

const { status, data } = await apiInstance.getJobApiCrmTenantJobsJobIdGet(
    tenant,
    jobId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **tenant** | [**number**] |  | defaults to undefined|
| **jobId** | [**number**] |  | defaults to undefined|


### Return type

**JobResponse**

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

