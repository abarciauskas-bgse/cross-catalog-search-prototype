from federated_search_api import FederatedSearch
import json
import requests

def test_two_cmr_results():
    name_search_term = 'LANDSAT'
    page=2
    size=2
    federated_search = FederatedSearch(
        name_search_term=name_search_term,
        page=page,
        size=size
    )
    lib_results = federated_search.search()
    lib_ids = [collection.id for collection in lib_results['results']]
    cmr_endpoint = federated_search.cmr_search_endpoint(federated_search.catalogs[0])
    cmr_response = requests.get(cmr_endpoint)
    cmr_results = json.loads(cmr_response.text)['items']
    cmr_ids = [cmr_collection['meta']['concept-id'] for cmr_collection in cmr_results]
    assert(lib_ids == cmr_ids)

def test_single_stac():
    name_search_term = 'BIOSAR'
    federated_search = FederatedSearch(name_search_term=name_search_term)
    lib_results = federated_search.search()
    lib_ids = [collection.id for collection in lib_results['results']]
    assert(lib_ids == ['BIOSAR1'])

def check_sublist(full_list, subset_list):
    return all(item in full_list for item in subset_list)

def test_mixed_results():
    name_search_term = 'gedi'
    page=1
    size=10
    federated_search = FederatedSearch(
        name_search_term=name_search_term,
        page=page,
        size=size
    )
    lib_results = federated_search.search()
    lib_ids = [collection.id for collection in lib_results['results']]
    stac_ids = ['GEDI02_B', 'GEDI02_A']
    # get CMR results
    cmr_endpoint = federated_search.cmr_search_endpoint(federated_search.catalogs[0])
    cmr_response = requests.get(cmr_endpoint)
    cmr_results = json.loads(cmr_response.text)['items']
    cmr_ids = [cmr_collection['meta']['concept-id'] for cmr_collection in cmr_results]
    assert(check_sublist(lib_ids, cmr_ids))
    assert(check_sublist(lib_ids, stac_ids))
    # len of results should be 4 since I get 14 results in Earthdata search    

def test_context_matches():
    name_search_term = 'gedi'
    page=1
    size=10
    federated_search = FederatedSearch(
        name_search_term=name_search_term,
        page=page,
        size=size
    )
    lib_results = federated_search.search()
    expected_context_results = {
        "matches": {
            "NASA Operational Results": 7,
            "MAAP Results": 2
            }
        }
    assert(lib_results['context'] == expected_context_results)