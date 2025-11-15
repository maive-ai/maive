# CredentialsApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**createCrmCredentialsApiCredsPost**](#createcrmcredentialsapicredspost) | **POST** /api/creds | Create Crm Credentials|
|[**deleteCrmCredentialsApiCredsDelete**](#deletecrmcredentialsapicredsdelete) | **DELETE** /api/creds | Delete Crm Credentials|
|[**getCrmCredentialsApiCredsGet**](#getcrmcredentialsapicredsget) | **GET** /api/creds | Get Crm Credentials|

# **createCrmCredentialsApiCredsPost**
> CRMCredentials createCrmCredentialsApiCredsPost(cRMCredentialsCreate)

Create or update CRM credentials for the user\'s organization.  If credentials already exist, they will be deactivated and new ones created.  Args:     data: CRM credentials data (provider and credentials dict)     current_user: Current authenticated user     creds_service: Credentials service  Returns:     Created credentials record (without actual credential values)  Raises:     HTTPException: If user has no organization or creation fails

### Example

```typescript
import {
    CredentialsApi,
    Configuration,
    CRMCredentialsCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new CredentialsApi(configuration);

let cRMCredentialsCreate: CRMCredentialsCreate; //

const { status, data } = await apiInstance.createCrmCredentialsApiCredsPost(
    cRMCredentialsCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **cRMCredentialsCreate** | **CRMCredentialsCreate**|  | |


### Return type

**CRMCredentials**

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

# **deleteCrmCredentialsApiCredsDelete**
> deleteCrmCredentialsApiCredsDelete()

Delete CRM credentials for the user\'s organization.  This removes credentials from both Secrets Manager and the database.  Args:     current_user: Current authenticated user     creds_service: Credentials service  Raises:     HTTPException: If user has no organization or credentials not found

### Example

```typescript
import {
    CredentialsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CredentialsApi(configuration);

const { status, data } = await apiInstance.deleteCrmCredentialsApiCredsDelete();
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

# **getCrmCredentialsApiCredsGet**
> CRMCredentials getCrmCredentialsApiCredsGet()

Get CRM credentials configuration for the user\'s organization.  Note: This endpoint does NOT return the actual credential values, only the metadata (provider type, created date, etc.).  Args:     current_user: Current authenticated user     db: Database session  Returns:     Credentials metadata (no actual secrets)  Raises:     HTTPException: If user has no organization or credentials not found

### Example

```typescript
import {
    CredentialsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new CredentialsApi(configuration);

const { status, data } = await apiInstance.getCrmCredentialsApiCredsGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**CRMCredentials**

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

