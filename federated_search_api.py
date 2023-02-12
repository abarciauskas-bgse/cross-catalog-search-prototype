import boto3
import codecs
import csv
from fastapi import FastAPI, APIRouter, Query
from fastapi_pagination import Page, add_pagination, paginate
from fastapi_pagination.default import Page as BasePage, Params as BaseParams
import json
import pandas as pd
import pprint
from pydantic import BaseModel
from stac_pydantic import Collection
import re
import requests
from typing import Dict, TypeVar, Generic

s3_client = boto3.client('s3')

app = FastAPI(
    title='MAAP Federated Search',
    version='0.0.beta',
    root_path='',
)

router = APIRouter()
app.include_router(router, tags=["Search"])
T = TypeVar("T")


class Params(BaseParams):
    size: int = Query(10, ge=1, le=100, description="Page size")

class Page(BasePage[T], Generic[T]):
    __params_type__ = Params

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get(
    "/search",
    summary="Retrieve all matching collections",
    operation_id="search",
    response_model=Page[Collection]
)
async def search(
    bbox: str = None, # description="Bounding box in xmin,ymin,xmax,ymax"
    temporal: str = None, # description="Start and end date to query"
    name_search_term: str = None, # description="Name to search for in short names and titles"
    page: int = 1,
    size: int = Params().size
):
    federated_search = FederatedSearch(
        bbox=bbox,
        temporal=temporal,
        name_search_term=name_search_term,
        page=page,
        size=size
    )
    results = federated_search.search()
    return paginate(results)

@app.get(
    "/search_links",
    summary="Retrieve all matching collections",
    operation_id="search",
    response_model=Page[Dict]
)
async def search_links(
    bbox: str = None, # description="Bounding box in xmin,ymin,xmax,ymax"
    temporal: str = None, # description="Start and end date to query"
    name_search_term: str = None, # description="Name to search for in short names and titles"
):
    federated_search = FederatedSearch(bbox=bbox, temporal=temporal, name_search_term=name_search_term, links_only=True)
    results = federated_search.search()
    return paginate(results)

add_pagination(app)

class FederatedSearch(BaseModel):
    catalogs: list[dict] = [{
        'name': 'NASA Operational',
        'endpoint': 'https://cmr.earthdata.nasa.gov',
        'type': 'cmr'
    },{
        'name': 'MAAP',
        'endpoint': 'https://stac.maap-project.org',
        'type': 'stac'        
    }]
    bbox: str = None
    temporal: str = None
    name_search_term: str = None
    results: list = []
    page_limit: int = 20
    total_results_per_catalog_limit: int = 20
    links_only = False

    def stac_search(
        self,
        catalog: Dict         
    ):
        # There's no collections search by bbox and temporal parameters, so we just return all stac items with the items search endpoint
        results = []
        response = requests.get(f"{catalog['endpoint']}/collections")
        maap_collections = json.loads(response.text)['collections']
        for collection in maap_collections:
            short_name = collection['id']
            title = collection['title']
            stac_url = f"{catalog['endpoint']}/{short_name}"
            collection_matches_search = False
            if collection.get('short_name'):
                if re.search(self.name_search_term, collection.get('short_name'), re.IGNORECASE):
                    collection_matches_search = True
            if not collection_matches_search and collection.get('title'):
                if re.search(self.name_search_term, collection.get('title'), re.IGNORECASE):
                    collection_matches_search = True
            if collection_matches_search:
                #Do we want to return a simplified response or the actual response?
                collection_json = {
                    'short_name': short_name,
                    'title': title,
                    'stac_url': stac_url,
                    'cmr_url': None,
                    'items_url': f"{stac_url}/items?bounding_box={self.bbox}&temporal={self.temporal}"
                }
                if self.links_only:
                    results.append(collection_json)
                else:
                    collection['summaries'] = {k: v for k, v in collection['summaries'].items() if v is not None}
                    results.append(Collection(**collection))
        return results

    def cmr_search(self, catalog):
        query_response_data = [True]
        results_per_catalog = 0
        page_num = 1
        results = []
        while len(query_response_data) > 0 and results_per_catalog < self.total_results_per_catalog_limit:
            # https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#c-bounding-box
            # lower left longitude, lower left latitude, upper right longitude, upper right latitude.  
            # bounding_box[]=-10,-5,10,5
            # https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#c-temporal
            # The temporal datetime has to be in yyyy-MM-ddTHH:mm:ssZ format.
            # temporal[]=2000-01-01T10:00:00Z,2010-03-10T12:00:00Z,30,60
            search_endpoint = f"{catalog['endpoint']}/search/collections.umm_json?" + \
                f"entry_title[]=*{self.name_search_term}*&options[entry_title][pattern]=true&options[entry_title][ignore_case]=true"
            if self.bbox:
                search_endpoint = f"{search_endpoint}&bounding_box[]={self.bbox}"
            if self.temporal:
                search_endpoint = f"{search_endpoint}&temporal[]={self.temporal}"           
            search_endpoint = f"{search_endpoint}&page_num={page_num}&page_size={self.page_limit}"
            query_response = requests.get(search_endpoint)
            query_response_data = json.loads(query_response.text)['items']
            for collection in query_response_data:
                short_name, version = collection['umm']['ShortName'], collection['umm']['Version']
                concept_id = collection['meta']['concept-id']
                stac_url = f"{catalog['endpoint']}/concepts/{concept_id}.stac"
                items_url = f"{catalog['endpoint']}/granules.stac?short_name={short_name}&version={version}"
                if self.bbox:
                    items_url = f"{items_url}&bounding_box[]={self.bbox}"
                if self.temporal:
                    items_url = f"{items_url}&temporal[]={self.temporal}"
                if self.links_only:
                    results.append({
                        'short_name': short_name,
                        'title': collection.get('EntryTitle'),
                        'version': version,
                        'cmr_url': f"{catalog['endpoint']}/collections.json?short_name={short_name}&version={version}",
                        'stac_url': stac_url,
                        'items_url': items_url
                    })
                else:
                    stac_collection = requests.get(stac_url).json()
                    try:
                        results.append(Collection(**stac_collection))
                    except Exception as e:
                        print(f"Could not create STAC collection for {stac_url}.\nError: {e}.")
            page_num += 1
            results_per_catalog += len(results)
        return results
  
    def search(self):
        results = []
        for catalog in self.catalogs:
            if catalog['type'] == 'stac':
                results.extend(self.stac_search(catalog=catalog))
            elif catalog['type'] == 'cmr':
                results.extend(self.cmr_search(catalog=catalog))
        return results


