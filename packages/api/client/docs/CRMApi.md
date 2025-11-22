# CRMApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**addContactNoteApiCrmContactsContactIdNotesPost**](#addcontactnoteapicrmcontactscontactidnotespost) | **POST** /api/crm/contacts/{contact_id}/notes | Add Contact Note|
|[**addJobNoteApiCrmJobsJobIdNotesPost**](#addjobnoteapicrmjobsjobidnotespost) | **POST** /api/crm/jobs/{job_id}/notes | Add Job Note|
|[**createMockProjectApiCrmProjectsPost**](#createmockprojectapicrmprojectspost) | **POST** /api/crm/projects | Create Mock Project|
|[**downloadFileApiCrmFilesFileIdDownloadGet**](#downloadfileapicrmfilesfileiddownloadget) | **GET** /api/crm/files/{file_id}/download | Download File|
|[**getAllContactsApiCrmContactsGet**](#getallcontactsapicrmcontactsget) | **GET** /api/crm/contacts | Get All Contacts|
|[**getAllJobsApiCrmJobsGet**](#getalljobsapicrmjobsget) | **GET** /api/crm/jobs | Get All Jobs|
|[**getAllProjectsApiCrmProjectsGet**](#getallprojectsapicrmprojectsget) | **GET** /api/crm/projects | Get All Projects|
|[**getContactApiCrmContactsContactIdGet**](#getcontactapicrmcontactscontactidget) | **GET** /api/crm/contacts/{contact_id} | Get Contact|
|[**getJobApiCrmJobsJobIdGet**](#getjobapicrmjobsjobidget) | **GET** /api/crm/jobs/{job_id} | Get Job|
|[**getJobFilesApiCrmJobsJobIdFilesGet**](#getjobfilesapicrmjobsjobidfilesget) | **GET** /api/crm/jobs/{job_id}/files | Get Job Files|
|[**getProjectApiCrmProjectsProjectIdGet**](#getprojectapicrmprojectsprojectidget) | **GET** /api/crm/projects/{project_id} | Get Project|
|[**updateJobStatusApiCrmJobsJobIdStatusPatch**](#updatejobstatusapicrmjobsjobidstatuspatch) | **PATCH** /api/crm/jobs/{job_id}/status | Update Job Status|
|[**updateMockProjectApiCrmProjectsProjectIdPatch**](#updatemockprojectapicrmprojectsprojectidpatch) | **PATCH** /api/crm/projects/{project_id} | Update Mock Project|
|[**updateProjectStatusApiCrmProjectsProjectIdStatusPatch**](#updateprojectstatusapicrmprojectsprojectidstatuspatch) | **PATCH** /api/crm/projects/{project_id}/status | Update Project Status|

# **addContactNoteApiCrmContactsContactIdNotesPost**
> Note addContactNoteApiCrmContactsContactIdNotesPost(bodyAddContactNoteApiCrmContactsContactIdNotesPost)

Add a note to a contact.  This endpoint works across all CRM providers and returns a standardized Note schema.  Args:     contact_id: The unique identifier for the contact     text: The text content of the note     pin_to_top: Whether to pin the note to the top (provider-specific, may not be supported)     crm_service: The CRM service instance from dependency injection  Returns:     Note: The created note in universal format  Raises:     HTTPException: If the contact is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration,
    BodyAddContactNoteApiCrmContactsContactIdNotesPost
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let contactId: string; // (default to undefined)
let bodyAddContactNoteApiCrmContactsContactIdNotesPost: BodyAddContactNoteApiCrmContactsContactIdNotesPost; //

const { status, data } = await apiInstance.addContactNoteApiCrmContactsContactIdNotesPost(
    contactId,
    bodyAddContactNoteApiCrmContactsContactIdNotesPost
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyAddContactNoteApiCrmContactsContactIdNotesPost** | **BodyAddContactNoteApiCrmContactsContactIdNotesPost**|  | |
| **contactId** | [**string**] |  | defaults to undefined|


### Return type

**Note**

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

# **addJobNoteApiCrmJobsJobIdNotesPost**
> Note addJobNoteApiCrmJobsJobIdNotesPost(bodyAddJobNoteApiCrmJobsJobIdNotesPost)

Add a note to a job.  This endpoint works across all CRM providers and returns a standardized Note schema.  Args:     job_id: The unique identifier for the job     text: The text content of the note     pin_to_top: Whether to pin the note to the top (provider-specific, may not be supported)     crm_service: The CRM service instance from dependency injection  Returns:     Note: The created note in universal format  Raises:     HTTPException: If the job is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration,
    BodyAddJobNoteApiCrmJobsJobIdNotesPost
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let jobId: string; // (default to undefined)
let bodyAddJobNoteApiCrmJobsJobIdNotesPost: BodyAddJobNoteApiCrmJobsJobIdNotesPost; //

const { status, data } = await apiInstance.addJobNoteApiCrmJobsJobIdNotesPost(
    jobId,
    bodyAddJobNoteApiCrmJobsJobIdNotesPost
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyAddJobNoteApiCrmJobsJobIdNotesPost** | **BodyAddJobNoteApiCrmJobsJobIdNotesPost**|  | |
| **jobId** | [**string**] |  | defaults to undefined|


### Return type

**Note**

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

# **createMockProjectApiCrmProjectsPost**
> Project createMockProjectApiCrmProjectsPost(mockProject)

Create a new demo project (Mock CRM only).  This endpoint is only available when using the Mock CRM provider. It allows creating demo projects for testing and demonstrations.  Args:     request: The project data to create     current_user: The authenticated user     crm_service: The CRM service instance  Returns:     Project: The created project  Raises:     HTTPException: If not using Mock CRM or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration,
    MockProject
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let mockProject: MockProject; //

const { status, data } = await apiInstance.createMockProjectApiCrmProjectsPost(
    mockProject
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **mockProject** | **MockProject**|  | |


### Return type

**Project**

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

# **downloadFileApiCrmFilesFileIdDownloadGet**
> any downloadFileApiCrmFilesFileIdDownloadGet()

Download a specific file\'s content.  This endpoint streams the file content to the client with proper headers for browser download.  Args:     file_id: The unique identifier for the file     filename: Optional filename (recommended to provide from file list)     content_type: Optional content type (recommended to provide from file list)     crm_service: The CRM service instance from dependency injection  Returns:     StreamingResponse with file content  Raises:     HTTPException: If the file is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let fileId: string; // (default to undefined)
let filename: string; //Optional filename from metadata (optional) (default to undefined)
let contentType: string; //Optional content type from metadata (optional) (default to undefined)

const { status, data } = await apiInstance.downloadFileApiCrmFilesFileIdDownloadGet(
    fileId,
    filename,
    contentType
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fileId** | [**string**] |  | defaults to undefined|
| **filename** | [**string**] | Optional filename from metadata | (optional) defaults to undefined|
| **contentType** | [**string**] | Optional content type from metadata | (optional) defaults to undefined|


### Return type

**any**

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

# **getAllContactsApiCrmContactsGet**
> ContactList getAllContactsApiCrmContactsGet()

Get all contacts with pagination.  This endpoint works across all CRM providers and returns a standardized ContactList schema.  Args:     page: Page number (1-indexed)     page_size: Number of items per page (max 100)     crm_service: The CRM service instance from dependency injection  Returns:     ContactList: Paginated list of contacts in universal format  Raises:     HTTPException: If an error occurs while fetching contacts

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let page: number; //Page number (1-indexed) (optional) (default to 1)
let pageSize: number; //Number of items per page (optional) (default to 50)

const { status, data } = await apiInstance.getAllContactsApiCrmContactsGet(
    page,
    pageSize
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **page** | [**number**] | Page number (1-indexed) | (optional) defaults to 1|
| **pageSize** | [**number**] | Number of items per page | (optional) defaults to 50|


### Return type

**ContactList**

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

# **getAllJobsApiCrmJobsGet**
> JobList getAllJobsApiCrmJobsGet()

Get all jobs with pagination.  This endpoint works across all CRM providers and returns a standardized JobList schema.  Args:     page: Page number (1-indexed)     page_size: Number of items per page (max 100)     search: Optional search query to filter jobs     crm_service: The CRM service instance from dependency injection  Returns:     JobList: Paginated list of jobs in universal format  Raises:     HTTPException: If an error occurs while fetching jobs

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let page: number; //Page number (1-indexed) (optional) (default to 1)
let pageSize: number; //Number of items per page (optional) (default to 50)
let search: string; //Search query to filter jobs by name, address, phone, or claim number (optional) (default to undefined)

const { status, data } = await apiInstance.getAllJobsApiCrmJobsGet(
    page,
    pageSize,
    search
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **page** | [**number**] | Page number (1-indexed) | (optional) defaults to 1|
| **pageSize** | [**number**] | Number of items per page | (optional) defaults to 50|
| **search** | [**string**] | Search query to filter jobs by name, address, phone, or claim number | (optional) defaults to undefined|


### Return type

**JobList**

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

# **getAllProjectsApiCrmProjectsGet**
> ProjectList getAllProjectsApiCrmProjectsGet()

Get all projects with pagination.  This endpoint works across all CRM providers and returns a standardized ProjectList schema.  Args:     page: Page number (1-indexed)     page_size: Number of items per page (max 100)     search: Optional search query to filter projects     crm_service: The CRM service instance from dependency injection  Returns:     ProjectList: Paginated list of projects in universal format  Raises:     HTTPException: If an error occurs while fetching projects

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let page: number; //Page number (1-indexed) (optional) (default to 1)
let pageSize: number; //Number of items per page (optional) (default to 50)
let search: string; //Search query to filter projects by name, address, phone, or claim number (optional) (default to undefined)

const { status, data } = await apiInstance.getAllProjectsApiCrmProjectsGet(
    page,
    pageSize,
    search
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **page** | [**number**] | Page number (1-indexed) | (optional) defaults to 1|
| **pageSize** | [**number**] | Number of items per page | (optional) defaults to 50|
| **search** | [**string**] | Search query to filter projects by name, address, phone, or claim number | (optional) defaults to undefined|


### Return type

**ProjectList**

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

# **getContactApiCrmContactsContactIdGet**
> Contact getContactApiCrmContactsContactIdGet()

Get a specific contact by ID.  This endpoint works across all CRM providers and returns a standardized Contact schema.  Args:     contact_id: The unique identifier for the contact (provider-specific format)     crm_service: The CRM service instance from dependency injection  Returns:     Contact: The contact information in universal format  Raises:     HTTPException: If the contact is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let contactId: string; // (default to undefined)

const { status, data } = await apiInstance.getContactApiCrmContactsContactIdGet(
    contactId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **contactId** | [**string**] |  | defaults to undefined|


### Return type

**Contact**

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

# **getJobApiCrmJobsJobIdGet**
> Job getJobApiCrmJobsJobIdGet()

Get a specific job by ID.  This endpoint works across all CRM providers and returns a standardized Job schema.  Args:     job_id: The unique identifier for the job (provider-specific format)     crm_service: The CRM service instance from dependency injection  Returns:     Job: The job information in universal format  Raises:     HTTPException: If the job is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let jobId: string; // (default to undefined)

const { status, data } = await apiInstance.getJobApiCrmJobsJobIdGet(
    jobId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **jobId** | [**string**] |  | defaults to undefined|


### Return type

**Job**

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

# **getJobFilesApiCrmJobsJobIdFilesGet**
> any getJobFilesApiCrmJobsJobIdFilesGet()

Get files attached to a specific job with optional type filtering.  This endpoint returns metadata for files/attachments associated with a job. Supports filtering by file type (all, images, or pdfs).  Args:     job_id: The unique identifier for the job     file_filter: Filter by type - \"all\", \"images\", or \"pdfs\" (default: \"all\")     crm_service: The CRM service instance from dependency injection  Returns:     List of file metadata dictionaries containing:     - id: File identifier     - filename: Original filename     - content_type: MIME type     - size: File size in bytes     - record_type_name: Type of file (Photo, Document, etc.)     - description: Optional file description     - date_created: Unix timestamp of creation     - created_by_name: Name of uploader     - is_private: Whether file is private  Raises:     HTTPException: If an error occurs fetching files

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let jobId: string; // (default to undefined)
let fileFilter: string; //Filter by type: \'all\', \'images\', or \'pdfs\' (optional) (default to 'all')

const { status, data } = await apiInstance.getJobFilesApiCrmJobsJobIdFilesGet(
    jobId,
    fileFilter
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **jobId** | [**string**] |  | defaults to undefined|
| **fileFilter** | [**string**] | Filter by type: \&#39;all\&#39;, \&#39;images\&#39;, or \&#39;pdfs\&#39; | (optional) defaults to 'all'|


### Return type

**any**

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

# **getProjectApiCrmProjectsProjectIdGet**
> Project getProjectApiCrmProjectsProjectIdGet()

Get a specific project by ID.  This endpoint works across all CRM providers and returns a standardized Project schema.  Note: In flat CRMs like JobNimbus, projects and jobs are the same entity.  Args:     project_id: The unique identifier for the project (provider-specific format)     crm_service: The CRM service instance from dependency injection  Returns:     Project: The project information in universal format  Raises:     HTTPException: If the project is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let projectId: string; // (default to undefined)

const { status, data } = await apiInstance.getProjectApiCrmProjectsProjectIdGet(
    projectId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **projectId** | [**string**] |  | defaults to undefined|


### Return type

**Project**

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

# **updateJobStatusApiCrmJobsJobIdStatusPatch**
> updateJobStatusApiCrmJobsJobIdStatusPatch(bodyUpdateJobStatusApiCrmJobsJobIdStatusPatch)

Update the status of a job.  This endpoint works across all CRM providers.  Args:     job_id: The unique identifier for the job     status_value: The new status value (provider-specific format)     crm_service: The CRM service instance from dependency injection  Raises:     HTTPException: If the job is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration,
    BodyUpdateJobStatusApiCrmJobsJobIdStatusPatch
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let jobId: string; // (default to undefined)
let bodyUpdateJobStatusApiCrmJobsJobIdStatusPatch: BodyUpdateJobStatusApiCrmJobsJobIdStatusPatch; //

const { status, data } = await apiInstance.updateJobStatusApiCrmJobsJobIdStatusPatch(
    jobId,
    bodyUpdateJobStatusApiCrmJobsJobIdStatusPatch
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyUpdateJobStatusApiCrmJobsJobIdStatusPatch** | **BodyUpdateJobStatusApiCrmJobsJobIdStatusPatch**|  | |
| **jobId** | [**string**] |  | defaults to undefined|


### Return type

void (empty response body)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**204** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **updateMockProjectApiCrmProjectsProjectIdPatch**
> Project updateMockProjectApiCrmProjectsProjectIdPatch(mockProject)

Update an existing demo project (Mock CRM only).  This endpoint is only available when using the Mock CRM provider. It allows updating demo projects for testing and demonstrations.  Args:     project_id: The unique identifier for the project     request: The updated project data     current_user: The authenticated user     crm_service: The CRM service instance  Returns:     Project: The updated project  Raises:     HTTPException: If not using Mock CRM or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration,
    MockProject
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let projectId: string; // (default to undefined)
let mockProject: MockProject; //

const { status, data } = await apiInstance.updateMockProjectApiCrmProjectsProjectIdPatch(
    projectId,
    mockProject
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **mockProject** | **MockProject**|  | |
| **projectId** | [**string**] |  | defaults to undefined|


### Return type

**Project**

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

# **updateProjectStatusApiCrmProjectsProjectIdStatusPatch**
> updateProjectStatusApiCrmProjectsProjectIdStatusPatch(bodyUpdateProjectStatusApiCrmProjectsProjectIdStatusPatch)

Update the status of a project.  This endpoint works across all CRM providers.  Args:     project_id: The unique identifier for the project     status_value: The new status value (provider-specific format)     crm_service: The CRM service instance from dependency injection  Raises:     HTTPException: If the project is not found or an error occurs

### Example

```typescript
import {
    CRMApi,
    Configuration,
    BodyUpdateProjectStatusApiCrmProjectsProjectIdStatusPatch
} from './api';

const configuration = new Configuration();
const apiInstance = new CRMApi(configuration);

let projectId: string; // (default to undefined)
let bodyUpdateProjectStatusApiCrmProjectsProjectIdStatusPatch: BodyUpdateProjectStatusApiCrmProjectsProjectIdStatusPatch; //

const { status, data } = await apiInstance.updateProjectStatusApiCrmProjectsProjectIdStatusPatch(
    projectId,
    bodyUpdateProjectStatusApiCrmProjectsProjectIdStatusPatch
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyUpdateProjectStatusApiCrmProjectsProjectIdStatusPatch** | **BodyUpdateProjectStatusApiCrmProjectsProjectIdStatusPatch**|  | |
| **projectId** | [**string**] |  | defaults to undefined|


### Return type

void (empty response body)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**204** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

