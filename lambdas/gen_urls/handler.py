import json
import requests
import csv
import boto3
from botocore.exceptions import ClientError

# Fetch all collections from Earthdata Cloud
# there's just under 2000 (1761)
# TODO(aimee): implement paging since the number is expected to grow
cmr_url = "https://cmr.earthdata.nasa.gov"

def earthdata_collections_url(cloud_hosted=None, page_num=1):
    url = f"{cmr_url}/search/collections.json?page_num={page_num}"
    if cloud_hosted:
        return f"{url}&cloud_hosted=true"
    else:
        return url

def gen_cmr_collections():
    # collect results in a list of tuples (short_name, title, stac_url, cmr_url)
    results = []
    earthdata_stac_url = f"{cmr_url}/stac"
    earthdata_collections = [True]
    page_num = 1
    while len(earthdata_collections) > 0:
        response = requests.get(earthdata_collections_url(page_num=page_num, cloud_hosted=True))
        earthdata_collections = json.loads(response.text)['feed']['entry']    
        for collection in earthdata_collections:
            short_name = collection['short_name']
            title = collection['title']
            daac = collection['data_center']
            version = collection['version_id']
            stac_url = f"{earthdata_stac_url}/{daac}/collections/{short_name}.v{version}"
            #response = requests.head(stac_url)
            if True: #response.status_code == 200:
                results.append((short_name, title, stac_url, f"{cmr_url}/collections.json?short_name={short_name}&version={version}"))
            else:
                print(f"No STAC record found for {stac_url}")
        page_num += 1
    return results

maap_url = "https://stac.maap-project.org/collections"
def gen_maap_collections():
    results = []
    response = requests.get(maap_url)
    maap_collections = json.loads(response.text)['collections']
    for collection in maap_collections:
        short_name = collection['id']
        title = collection['title']
        stac_url = f"{maap_url}/{short_name}"
        #response = requests.get(stac_url)
        if True: #response.status_code == 200:
            results.append((short_name, title, stac_url, None))
        else:
            print(f"No STAC record found for {stac_url}")
    return results

bucket = 'maap-stac-assets'
s3_client = boto3.client('s3')
def write_and_store_file(collections, filename = ''):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['short_name','title','stac_url','cmr_url'])
        for result in collections:
            writer.writerow(result)
        csvfile.close()
    try:
        response = s3_client.upload_file(
            filename,
            bucket,
            filename,
            ExtraArgs={'ACL': 'public-read'}
        )
    except ClientError as e:
        print(e)

def handler():
    cmr_data = gen_cmr_collections()
    write_and_store_file(cmr_data, 'nasa-operational-collections.csv')
    maap_data = gen_maap_collections()
    write_and_store_file(maap_data, 'maap-collections.csv')

if __name__ == "__main__":
    handler()