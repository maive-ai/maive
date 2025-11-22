# WorkflowsApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**callAndWriteResultsToCrmApiWorkflowsCallAndWriteResultsToCrmPost**](#callandwriteresultstocrmapiworkflowscallandwriteresultstocrmpost) | **POST** /api/workflows/call-and-write-results-to-crm | Call And Write Results To Crm|
|[**generateProjectSummaryApiWorkflowsGenerateProjectSummaryProjectIdPost**](#generateprojectsummaryapiworkflowsgenerateprojectsummaryprojectidpost) | **POST** /api/workflows/generate-project-summary/{project_id} | Generate Project Summary|

# **callAndWriteResultsToCrmApiWorkflowsCallAndWriteResultsToCrmPost**
> CallResponse callAndWriteResultsToCrmApiWorkflowsCallAndWriteResultsToCrmPost(callRequest)

Create an outbound call with monitoring and write results to CRM.  This workflow endpoint orchestrates: 1. Creating the call via Voice AI provider 2. Starting background call monitoring and writing results to CRM 3. Updating CRM with call results when complete  Args:     request: The call request with phone number and context     current_user: The authenticated user     workflow: The call monitoring and CRM writing workflow from dependency injection  Returns:     CallResponse: The call information  Raises:     HTTPException: If call creation fails

### Example

```typescript
import {
    WorkflowsApi,
    Configuration,
    CallRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowsApi(configuration);

let callRequest: CallRequest; //

const { status, data } = await apiInstance.callAndWriteResultsToCrmApiWorkflowsCallAndWriteResultsToCrmPost(
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

# **generateProjectSummaryApiWorkflowsGenerateProjectSummaryProjectIdPost**
> ProjectSummary generateProjectSummaryApiWorkflowsGenerateProjectSummaryProjectIdPost()

Generate an AI summary for a project.  This workflow endpoint: 1. Fetches the project with notes from CRM 2. Analyzes notes using OpenAI gpt-4o-mini 3. Returns a structured summary with:    - Brief project status summary    - Recent actions taken (2-3 bullet points)    - Next steps (2-3 bullet points)  Args:     project_id: The unique identifier for the project     _current_user: The authenticated user (used for auth, not accessed)     workflow: The project summary workflow from dependency injection  Returns:     ProjectSummary: AI-generated structured summary  Raises:     HTTPException: If the project is not found or an error occurs

### Example

```typescript
import {
    WorkflowsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new WorkflowsApi(configuration);

let projectId: string; // (default to undefined)

const { status, data } = await apiInstance.generateProjectSummaryApiWorkflowsGenerateProjectSummaryProjectIdPost(
    projectId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **projectId** | [**string**] |  | defaults to undefined|


### Return type

**ProjectSummary**

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

