# Cross-Catalog Search Prototype

Generate URLs from MAAP and NASA Operational Earthdata Cloud datasets

```sh
python gen_urls.py
```

Upload the index file:

```sh
aws s3 cp index.html s3://maap-stac-assets/ --acl public-read
```

Example API Queries:

