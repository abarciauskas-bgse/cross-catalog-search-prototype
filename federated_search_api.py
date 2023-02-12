import boto3
import codecs
import csv
from fastapi import FastAPI, APIRouter, Query
import json
import pandas as pd
from pydantic import BaseModel
import re
import requests
from typing import Dict

s3_client = boto3.client('s3')

app = FastAPI(
    title='MAAP Federated Search',
    version='0.0.beta',
    root_path='',
)

router = APIRouter()
app.include_router(router, tags=["Search"])

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get(
    "/search",
    #response_model=Dict,
    summary="Retrieve all matching collections",
    operation_id="search",
)
async def search(
    bbox: str = None, # description="Bounding box in xmin,ymin,xmax,ymax"
    temporal: str = None, # description="Start and end date to query"
    name_search_term: str = None # description="Name to search for in short names and titles"
):
    search_results = FederatedSearch(bbox=bbox, temporal=temporal, name_search_term=name_search_term)
    return search_results.search()

class FederatedSearch(BaseModel):
    catalogs: list[dict] = [{
        'name': 'NASA Operational',
        'endpoint': 'https://cmr.earthdata.nasa.gov',
        'type': 'cmr'
    },
    {
        'name': 'MAAP',
        'endpoint': 'https://stac.maap-project.org',
        'type': 'stac'        
    }
    ]
    bucket: str = 'maap-stac-assets'
    bbox: str = None
    temporal: str = None
    name_search_term: str = None
    results: list = []
    page_limit: int = 20
    total_results_per_catalog_limit: int = 100  

    def stac_search(
        self,
        catalog: Dict         
    ):
        # There's no collections search by bbox and temporal parameters, so we just return all stac items with the items search endpoint
        filename = f"{catalog['name'].lower().replace(' ', '-')}-collections.csv"
        results = []
        file_obj = s3_client.get_object(Bucket=self.bucket, Key=filename)
        for collection in csv.DictReader(codecs.getreader("utf-8")(file_obj["Body"])):
            collection_matches_search = False
            if collection.get('short_name'):
                if re.search(self.name_search_term, collection.get('short_name'), re.IGNORECASE):
                    collection_matches_search = True
            if not collection_matches_search and collection.get('title'):
                if re.search(self.name_search_term, collection.get('title'), re.IGNORECASE):
                    collection_matches_search = True
            if collection_matches_search:
                collection['items_url'] = f"{collection['stac_url']}/items?bounding_box={self.bbox}&temporal={self.temporal}"
                results.append(collection)
        return results

    def cmr_search(self, catalog):
        # TODO: if only searching by name/title, can load from static file
        # otherwise use search
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
            search_endpoint = f"{catalog['endpoint']}/search/collections.json?" + \
                f"entry_title[]=*{self.name_search_term}*&options[entry_title][pattern]=true&options[entry_title][ignore_case]=true"
            if self.bbox:
                search_endpoint = f"{search_endpoint}&bounding_box[]={self.bbox}"
            if self.temporal:
                search_endpoint = f"{search_endpoint}&temporal[]={self.temporal}"                    
            search_endpoint = f"{search_endpoint}&page_num={page_num}&page_size={self.page_limit}"
            print(search_endpoint)
            query_response = requests.get(search_endpoint)
            query_response_data = json.loads(query_response.text)['feed']['entry']
            for collection in query_response_data:
                short_name, version = collection['short_name'], collection['version_id']
                results.append({
                    'short_name': short_name,
                    'title': collection['title'],
                    'version': version,
                    'url': f"{catalog['endpoint']}/collections.json?short_name={short_name}&version={version}",
                })
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


