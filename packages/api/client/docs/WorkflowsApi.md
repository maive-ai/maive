# WorkflowsApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**callAndWriteResultsToCrmApiWorkflowsCallAndWriteResultsToCrmPost**](#callandwriteresultstocrmapiworkflowscallandwriteresultstocrmpost) | **POST** /api/workflows/call-and-write-results-to-crm | Call And Write Results To Crm|

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

