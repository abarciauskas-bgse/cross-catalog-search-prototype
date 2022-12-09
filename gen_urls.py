import json
import requests
import csv
import boto3
from botocore.exceptions import ClientError

# collect results in a list of tuples (short_name, stac_url, cmr_url)
results = []

# Fetch all collections from Earthdata Cloud
# there's just under 2000 (1761)
# TODO(aimee): implement paging since the number is expected to grow
limit = 2000
cmr_url = "https://cmr.earthdata.nasa.gov"
earthdata_cloud_collections_url = f"{cmr_url}/search/collections.json?cloud_hosted=true&page_size={limit}"

def gen_cmr_collections():
    response = requests.get(earthdata_cloud_collections_url)
    earthdata_cloud_collections = json.loads(response.text)['feed']['entry']
    earthdata_stac_url = f"{cmr_url}/cloudstac"
    for collection in earthdata_cloud_collections:
        short_name = collection['short_name']
        daac = collection['data_center']
        version = collection['version_id']
        stac_url = f"{earthdata_stac_url}/{daac}/collections/{short_name}.v{version}"
        response = requests.head(stac_url)
        if response.status_code == 200:
            results.append((short_name, stac_url, f"{cmr_url}/collections.json?short_name={short_name}&version={version}"))
        else:
            print(f"No STAC record found for {stac_url}")

    filename = 'nasa-operational-collections.csv'
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['short_name','stac_url','cmr_url'])
        for result in results:
            writer.writerow(result)
        csvfile.close()
    return filename

bucket = 'maap-stac-assets'
s3_client = boto3.client('s3')
def store_file(filename):
    # Store a CSV on S3
    try:
        response = s3_client.upload_file(
            filename,
            bucket,
            filename,
            ExtraArgs={'ACL': 'public-read'}
        )
    except ClientError as e:
        print(e)

maap_url = "https://stac.maap-project.org/collections"
def gen_maap_collections():
    response = requests.get(maap_url)
    maap_collections = json.loads(response.text)['collections']
    for collection in maap_collections:
        short_name = collection['id']
        stac_url = f"{maap_url}/{short_name}"
        response = requests.get(stac_url)
        if response.status_code == 200:
            results.append((short_name, stac_url))
        else:
            print(f"No STAC record found for {stac_url}")

    filename = 'maap-collections.csv'
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['short_name','stac_url'])
        for result in results:
            writer.writerow(result)
        csvfile.close()
    return filename

if __name__ == "__main__":
    #nasa_operational_data_file = gen_cmr_collections()
    #store_file(nasa_operational_data_file)

    maap_data_file = gen_maap_collections()
    store_file(maap_data_file)
