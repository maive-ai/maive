# PhoneNumbersApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**assignPhoneNumberApiPhoneNumbersPost**](#assignphonenumberapiphonenumberspost) | **POST** /api/phone-numbers | Assign Phone Number|
|[**deletePhoneNumberApiPhoneNumbersDelete**](#deletephonenumberapiphonenumbersdelete) | **DELETE** /api/phone-numbers | Delete Phone Number|
|[**getPhoneNumberApiPhoneNumbersGet**](#getphonenumberapiphonenumbersget) | **GET** /api/phone-numbers | Get Phone Number|

# **assignPhoneNumberApiPhoneNumbersPost**
> PhoneNumberResponse assignPhoneNumberApiPhoneNumbersPost(phoneNumberCreate)

Assign phone number to current user.  Args:     data: Phone number assignment data     current_user: Current authenticated user     service: Phone number service  Returns:     Created or updated configuration  Raises:     HTTPException: If assignment fails

### Example

```typescript
import {
    PhoneNumbersApi,
    Configuration,
    PhoneNumberCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new PhoneNumbersApi(configuration);

let phoneNumberCreate: PhoneNumberCreate; //

const { status, data } = await apiInstance.assignPhoneNumberApiPhoneNumbersPost(
    phoneNumberCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **phoneNumberCreate** | **PhoneNumberCreate**|  | |


### Return type

**PhoneNumberResponse**

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

# **deletePhoneNumberApiPhoneNumbersDelete**
> deletePhoneNumberApiPhoneNumbersDelete()

Remove phone number assignment for current user.  Args:     current_user: Current authenticated user     service: Phone number service

### Example

```typescript
import {
    PhoneNumbersApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PhoneNumbersApi(configuration);

const { status, data } = await apiInstance.deletePhoneNumberApiPhoneNumbersDelete();
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

# **getPhoneNumberApiPhoneNumbersGet**
> PhoneNumberResponse getPhoneNumberApiPhoneNumbersGet()

Get phone number for current user.  Args:     current_user: Current authenticated user     service: Phone number service  Returns:     User\'s phone number configuration  Raises:     HTTPException: If no phone number is configured

### Example

```typescript
import {
    PhoneNumbersApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new PhoneNumbersApi(configuration);

const { status, data } = await apiInstance.getPhoneNumberApiPhoneNumbersGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**PhoneNumberResponse**

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

