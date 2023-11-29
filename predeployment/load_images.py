from urllib.parse import urlparse
import boto3
import logging
import requests
from botocore.exceptions import ClientError
import os
import dload

my_bucket = "assessment3-s3749114"
json_file = "images.json"
img_attribute = "img_url"


# Creates new S3 bucket for hosting images
def create_bucket(bucket_name, region=None):
    print("Creating " + bucket_name + " bucket...")
    try:
        if region is None:
            s3_client = boto3.client('s3')
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client = boto3.client('s3', region_name=region)
            location = {'LocationConstraint': region}
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    except ClientError as e:
        logging.error(e)
        return False
    return True


# Downloads LoL Buddy logo and ranked emblem images from web to tmp file
def download_images():
    print("Downloading images to tmp file...")
    # Emblem images
    dload.save_unzip("https://static.developer.riotgames.com/docs/lol/ranked-emblems.zip", "tmp/")
    # Logo image
    url = "https://raw.githubusercontent.com/CarelleR/assessment3-s3749114/main/deployment/images/branding/Logo.png"
    a = urlparse(url)
    file_name = os.path.basename(a.path)
    r = requests.get(url, allow_redirects=True)
    open("tmp/" + file_name, 'wb').write(r.content)


# Uploads all images in tmp file to S3
def upload_all_image():
    print("Uploading images to s3...")
    directory = "tmp/"
    for f in os.listdir(directory):
        upload_image(directory, f)
    print("Finished uploading images to s3.")


# Uploads specified image to S3
def upload_image(directory, file_name):
    bucket = my_bucket
    s3 = boto3.resource('s3')
    try:
        s3.Bucket(bucket).upload_file(directory + file_name, file_name, ExtraArgs={'ACL': 'public-read'})
    except ClientError as e:
        logging.error(e)


# Clean up tmp file after finished uploading
def delete_tmp_files():
    print("Deleting tmp files...")
    directory = "tmp/"
    for f in os.listdir(directory):
        os.remove(os.path.join(directory, f))
    os.remove(os.path.join("", "ranked-emblems.zip"))
    print("Finished deleting tmp files")


if __name__ == '__main__':
    try:
        create_bucket(my_bucket)
        download_images()
        upload_all_image()
        delete_tmp_files()
    except:
        print("Couldn't load images. Check json or AWS credentials.")
