from decimal import Decimal
import json
from urllib.parse import urlparse
import os
import requests
import boto3

domain_name = "champions"


def delete_tmp_files():
    print("Deleting tmp files...")
    directory = "tmp/"
    for f in os.listdir(directory):
        os.remove(os.path.join(directory, f))


# Creates new json (in correct format) from champion.json for CloudSearch
# See champion_cloud_search.json file in predeployment_scripts directory to preview what it looks like
def make_cloud_search_json():
    if os.path.exists("champion_cloud_search.json"):
        os.remove(os.path.join("champion_cloud_search.json"))
    try:
        download_champion_json()
        with open("tmp/champion.json") as f:
            data = json.load(f, parse_float=Decimal)
        data_list = create_data(data)
        json_string = json.dumps(data_list)
        new_json_file = open("champion_cloud_search.json", "w")
        new_json_file.write(json_string)
        new_json_file.close()
    except:
        print("Couldn't make champion json file for CloudSearch.")


# Downloads champion json from LoL Data Dragon
def download_champion_json():
    print("Downloading champion json file...")
    url = "http://ddragon.leagueoflegends.com/cdn/12.20.1/data/en_US/champion.json"
    a = urlparse(url)
    file_name = os.path.basename(a.path)
    r = requests.get(url, allow_redirects=True)
    open("tmp/" + file_name, 'wb').write(r.content)


# Pulls out relevant information from the champion.json file and add to list
def create_data(champion_data):
    print("Creating CloudSearch file from champion json file...")
    champion_list = []
    for champion in champion_data["data"]:
        fields = {
            "name": champion_data["data"][champion]["name"],
            "tags": champion_data["data"][champion]["tags"],
            "id": champion_data["data"][champion]["id"],
            "difficulty": champion_data["data"][champion]["info"]["difficulty"],
            "image": champion_data["data"][champion]["image"]["full"]
        }
        champion_dict = {
            "id": champion_data["data"][champion]["key"],
            "type": "add",
            "fields": fields
        }
        champion_list.append(champion_dict)
    return champion_list


# Uploads new json file to CloudSearch
def update_cloud_search():
    try:
        print("Updating CloudSearch with json file...")
        client = boto3.client('cloudsearchdomain', endpoint_url="https://" + get_endpoint_url()['Endpoint'])
        champion_json = open("champion_cloud_search.json")
        json_loaded = json.load(champion_json)
        json_dump = json.dumps(json_loaded)
        client.upload_documents(documents=json_dump, contentType='application/json')
        champion_json.close()
    except:
        print("Error uploading data to CloudSearch.")
        print("If domain has recently been created, wait for it to finish processing and run indexing.")


# Gets CloudSearch domain
def get_endpoint_url():
    try:
        client = boto3.client('cloudsearch')
        info = client.describe_domains(DomainNames=[domain_name])
        endpoint_url = info['DomainStatusList'][0]['SearchService']
        return endpoint_url
    except:
        print("Could not get endpoint url.")
        print("If domain has recently been created, wait for it to finish processing and run indexing.")


# Makes new CloudSearch domain
def make_cloud_search_domain():
    print("Creating CloudSearch domain...")
    client = boto3.client("cloudsearch")
    client.create_domain(DomainName=domain_name)


# Set CloudSearch accss policy
def set_access_policy():
    print("Seting access policy...")
    client = boto3.client("cloudsearch")
    client.update_service_access_policies(
        DomainName=domain_name,
        AccessPolicies='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":["*"]},"Action":["cloudsearch:*"]}]}')


# Defines index fields for CloudSearch
def set_indices():
    print("Setting indices...")
    client = boto3.client("cloudsearch")
    indices = [
        {
            'IndexFieldName': 'name',
            'IndexFieldType': 'text',
            'TextOptions': {
                'ReturnEnabled': True,
                'SortEnabled': True,
                'HighlightEnabled': True,
                'AnalysisScheme': '_en_default_'
            }
        },
        {
            'IndexFieldName': 'image',
            'IndexFieldType': 'text',
            'TextOptions': {
                'ReturnEnabled': True,
                'SortEnabled': True,
                'HighlightEnabled': True,
                'AnalysisScheme': '_en_default_'
            },
        },
        {
            'IndexFieldName': 'id',
            'IndexFieldType': 'text',
            'TextOptions': {
                'ReturnEnabled': True,
                'SortEnabled': True,
                'HighlightEnabled': True,
                'AnalysisScheme': '_en_default_'
            }
        },
        {
            'IndexFieldName': 'tags',
            'IndexFieldType': 'text-array',
            'TextArrayOptions': {
                'ReturnEnabled': True,
                'HighlightEnabled': True,
                'AnalysisScheme': '_en_default_'
            }
        },
        {
            'IndexFieldName': 'difficulty',
            'IndexFieldType': 'int',
            'IntOptions': {
                'FacetEnabled': True,
                'SearchEnabled': True,
                'ReturnEnabled': True,
                'SortEnabled': True
            },
        },
    ]
    for index in indices:
        client.define_index_field(DomainName=domain_name, IndexField=index)


def print_menu():
    print("----------------------------------")
    print("MENU")
    print("----------------------------------")
    print("1 - Set up new CloudSearch")
    print("2 - Make json for CloudSearch")
    print("3 - Upload json to CloudSearch")
    print("4 - Clean up temp files")
    print("5 - Exit")
    print("----------------------------------")
    print("Enter choice: ")


if __name__ == '__main__':
    user_input = 0
    while user_input != 5:
        print_menu()
        user_input = int(input())
        if user_input == 1:
            make_cloud_search_domain()
            set_access_policy()
            set_indices()
        elif user_input == 2:
            make_cloud_search_json()
        elif user_input == 3:
            update_cloud_search()
        elif user_input == 5:
            delete_tmp_files()
        elif user_input == 6:
            print("Exiting...")
            quit()

