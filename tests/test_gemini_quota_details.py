import httpx
from cronos.providers import quota_details

def test_quota_categories_and_retry_are_sanitized():
    response=httpx.Response(429,json={'error':{'message':'private key and question','details':[
        {'@type':'type.googleapis.com/google.rpc.QuotaFailure','violations':[
            {'quotaId':'GenerateRequestsPerDayPerProjectPerModel-FreeTier','description':'private'},
            {'quotaId':'GenerateContentInputTokensPerModelPerMinute','quotaDimensions':{'private':'secret'}}]},
        {'@type':'type.googleapis.com/google.rpc.RetryInfo','retryDelay':'32.5s'}]}})
    assert quota_details(response)==(['requisições por dia','tokens por minuto'],32.5)

def test_unrecognized_provider_details_do_not_get_echoed():
    assert quota_details(httpx.Response(429,json={'error':{'details':[None,{'@type':'QuotaFailure','violations':[None,{'quotaId':'private-secret'}]}]}}))==([],None)
