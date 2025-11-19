# ScheduledGroupsApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**addProjectsToGroupApiScheduledGroupsGroupIdMembersPost**](#addprojectstogroupapischeduledgroupsgroupidmemberspost) | **POST** /api/scheduled-groups/{group_id}/members | Add Projects To Group|
|[**createScheduledGroupApiScheduledGroupsPost**](#createscheduledgroupapischeduledgroupspost) | **POST** /api/scheduled-groups/ | Create Scheduled Group|
|[**deleteScheduledGroupApiScheduledGroupsGroupIdDelete**](#deletescheduledgroupapischeduledgroupsgroupiddelete) | **DELETE** /api/scheduled-groups/{group_id} | Delete Scheduled Group|
|[**getScheduledGroupApiScheduledGroupsGroupIdGet**](#getscheduledgroupapischeduledgroupsgroupidget) | **GET** /api/scheduled-groups/{group_id} | Get Scheduled Group|
|[**listScheduledGroupsApiScheduledGroupsGet**](#listscheduledgroupsapischeduledgroupsget) | **GET** /api/scheduled-groups/ | List Scheduled Groups|
|[**markGoalCompletedApiScheduledGroupsGroupIdMembersProjectIdCompletedPatch**](#markgoalcompletedapischeduledgroupsgroupidmembersprojectidcompletedpatch) | **PATCH** /api/scheduled-groups/{group_id}/members/{project_id}/completed | Mark Goal Completed|
|[**removeProjectFromGroupApiScheduledGroupsGroupIdMembersProjectIdDelete**](#removeprojectfromgroupapischeduledgroupsgroupidmembersprojectiddelete) | **DELETE** /api/scheduled-groups/{group_id}/members/{project_id} | Remove Project From Group|
|[**toggleGroupActiveApiScheduledGroupsGroupIdActivePatch**](#togglegroupactiveapischeduledgroupsgroupidactivepatch) | **PATCH** /api/scheduled-groups/{group_id}/active | Toggle Group Active|
|[**updateScheduledGroupApiScheduledGroupsGroupIdPut**](#updatescheduledgroupapischeduledgroupsgroupidput) | **PUT** /api/scheduled-groups/{group_id} | Update Scheduled Group|

# **addProjectsToGroupApiScheduledGroupsGroupIdMembersPost**
> ScheduledGroupDetailResponse addProjectsToGroupApiScheduledGroupsGroupIdMembersPost(addProjectsToGroupRequest)

Add projects to a scheduled group.

### Example

```typescript
import {
    ScheduledGroupsApi,
    Configuration,
    AddProjectsToGroupRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ScheduledGroupsApi(configuration);

let groupId: number; // (default to undefined)
let addProjectsToGroupRequest: AddProjectsToGroupRequest; //

const { status, data } = await apiInstance.addProjectsToGroupApiScheduledGroupsGroupIdMembersPost(
    groupId,
    addProjectsToGroupRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **addProjectsToGroupRequest** | **AddProjectsToGroupRequest**|  | |
| **groupId** | [**number**] |  | defaults to undefined|


### Return type

**ScheduledGroupDetailResponse**

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

# **createScheduledGroupApiScheduledGroupsPost**
> ScheduledGroupResponse createScheduledGroupApiScheduledGroupsPost(createScheduledGroupRequest)

Create a new scheduled group.

### Example

```typescript
import {
    ScheduledGroupsApi,
    Configuration,
    CreateScheduledGroupRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ScheduledGroupsApi(configuration);

let createScheduledGroupRequest: CreateScheduledGroupRequest; //

const { status, data } = await apiInstance.createScheduledGroupApiScheduledGroupsPost(
    createScheduledGroupRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **createScheduledGroupRequest** | **CreateScheduledGroupRequest**|  | |


### Return type

**ScheduledGroupResponse**

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

# **deleteScheduledGroupApiScheduledGroupsGroupIdDelete**
> deleteScheduledGroupApiScheduledGroupsGroupIdDelete()

Delete a scheduled group.

### Example

```typescript
import {
    ScheduledGroupsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ScheduledGroupsApi(configuration);

let groupId: number; // (default to undefined)

const { status, data } = await apiInstance.deleteScheduledGroupApiScheduledGroupsGroupIdDelete(
    groupId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **groupId** | [**number**] |  | defaults to undefined|


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

# **getScheduledGroupApiScheduledGroupsGroupIdGet**
> ScheduledGroupDetailResponse getScheduledGroupApiScheduledGroupsGroupIdGet()

Get a scheduled group with its members.

### Example

```typescript
import {
    ScheduledGroupsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ScheduledGroupsApi(configuration);

let groupId: number; // (default to undefined)

const { status, data } = await apiInstance.getScheduledGroupApiScheduledGroupsGroupIdGet(
    groupId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **groupId** | [**number**] |  | defaults to undefined|


### Return type

**ScheduledGroupDetailResponse**

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

# **listScheduledGroupsApiScheduledGroupsGet**
> ScheduledGroupsListResponse listScheduledGroupsApiScheduledGroupsGet()

List all scheduled groups for the user.

### Example

```typescript
import {
    ScheduledGroupsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ScheduledGroupsApi(configuration);

const { status, data } = await apiInstance.listScheduledGroupsApiScheduledGroupsGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**ScheduledGroupsListResponse**

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

# **markGoalCompletedApiScheduledGroupsGroupIdMembersProjectIdCompletedPatch**
> ScheduledGroupMemberResponse markGoalCompletedApiScheduledGroupsGroupIdMembersProjectIdCompletedPatch()

Mark goal as completed for a project in a group.

### Example

```typescript
import {
    ScheduledGroupsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ScheduledGroupsApi(configuration);

let groupId: number; // (default to undefined)
let projectId: string; // (default to undefined)
let completed: boolean; // (optional) (default to true)

const { status, data } = await apiInstance.markGoalCompletedApiScheduledGroupsGroupIdMembersProjectIdCompletedPatch(
    groupId,
    projectId,
    completed
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **groupId** | [**number**] |  | defaults to undefined|
| **projectId** | [**string**] |  | defaults to undefined|
| **completed** | [**boolean**] |  | (optional) defaults to true|


### Return type

**ScheduledGroupMemberResponse**

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

# **removeProjectFromGroupApiScheduledGroupsGroupIdMembersProjectIdDelete**
> removeProjectFromGroupApiScheduledGroupsGroupIdMembersProjectIdDelete()

Remove a project from a scheduled group.

### Example

```typescript
import {
    ScheduledGroupsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ScheduledGroupsApi(configuration);

let groupId: number; // (default to undefined)
let projectId: string; // (default to undefined)

const { status, data } = await apiInstance.removeProjectFromGroupApiScheduledGroupsGroupIdMembersProjectIdDelete(
    groupId,
    projectId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **groupId** | [**number**] |  | defaults to undefined|
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

# **toggleGroupActiveApiScheduledGroupsGroupIdActivePatch**
> ScheduledGroupResponse toggleGroupActiveApiScheduledGroupsGroupIdActivePatch(updateGroupStatusRequest)

Start or stop a scheduled group.

### Example

```typescript
import {
    ScheduledGroupsApi,
    Configuration,
    UpdateGroupStatusRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ScheduledGroupsApi(configuration);

let groupId: number; // (default to undefined)
let updateGroupStatusRequest: UpdateGroupStatusRequest; //

const { status, data } = await apiInstance.toggleGroupActiveApiScheduledGroupsGroupIdActivePatch(
    groupId,
    updateGroupStatusRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **updateGroupStatusRequest** | **UpdateGroupStatusRequest**|  | |
| **groupId** | [**number**] |  | defaults to undefined|


### Return type

**ScheduledGroupResponse**

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

# **updateScheduledGroupApiScheduledGroupsGroupIdPut**
> ScheduledGroupResponse updateScheduledGroupApiScheduledGroupsGroupIdPut(updateScheduledGroupRequest)

Update a scheduled group.

### Example

```typescript
import {
    ScheduledGroupsApi,
    Configuration,
    UpdateScheduledGroupRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ScheduledGroupsApi(configuration);

let groupId: number; // (default to undefined)
let updateScheduledGroupRequest: UpdateScheduledGroupRequest; //

const { status, data } = await apiInstance.updateScheduledGroupApiScheduledGroupsGroupIdPut(
    groupId,
    updateScheduledGroupRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **updateScheduledGroupRequest** | **UpdateScheduledGroupRequest**|  | |
| **groupId** | [**number**] |  | defaults to undefined|


### Return type

**ScheduledGroupResponse**

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

