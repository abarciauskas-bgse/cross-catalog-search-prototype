# Cross-Catalog Search Prototype

This repo currently consists of 2 projects.

1. A simple UI built using static files on S3 to allow users to search across MAAP STAC and Earthdata Cloud datasets
2. An API for searching across MAAP STAC and CMR using name_search_term, bbox and temporal parameters.

## Files + UI for searching across MAAP STAC and Earthdata Cloud datasets

Generate URLs from MAAP and NASA Operational Earthdata Cloud datasets

```sh
export AWS_PROFILE=maap
python lambdas/gen_urls/handler.py
```

Upload the index file:

```sh
aws s3 cp index.html s3://maap-stac-assets/ --acl public-read
```

### TODOs:

* deploy cloudwatch events trigger + lambda function so files get updated regularly

## API

### Install

```bash
pip install -r requirements.txt
```

### Run

```
uvicorn federated_search_api:app --reloa
```

### Example API Queries:

Search for all collections which have a title or shortname like "LANDSAT"

```sh
http://127.0.0.1:8000/search?name_search_term=LANDSAT
http://127.0.0.1:8000/search_links?name_search_term=LANDSAT
http://127.0.0.1:8000/search?name_search_term=atl0&bbox=-10,-5,10,5
http://127.0.0.1:8000/search?name_search_term=atl0&temporal=2022-03-10T12:00:00Z,2023-01-10T12:00:00Z
http://127.0.0.1:8000/search?name_search_term=afrisar&page=2
```

### Docs

```
http://127.0.0.1:8000/docs
```


### TODOs

* Deployment of API

**IMPORTANT** right now too many results (e.g. "LANDSAT", 179 results, "SENTINEL", 295 results, "icesat", 88 results) takes minutes to load

* Smarter pagination - only read in the number of results required for the current page and size parameters
* Caching middleware or other caching strategy
* UI for API search - similar to other UI but with different results and more search parameters
* Search based on more parameters
