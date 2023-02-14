from federated_search_api import FederatedSearch
import requests
def test_pagination():
    name_search_term = 'LANDSAT'
    page=2
    size=2
    federated_search = FederatedSearch(
        name_search_term=name_search_term,
        page=page,
        size=size
    )
    lib_results = federated_search.search()
    print(lib_results)
    print()
    cmr_endpoint = federated_search.cmr_search_endpoint(federated_search.catalogs[0])
    cmr_results = requests.get(cmr_endpoint)
    print(json.loads(cmr_results.text)['items'])
    assert()