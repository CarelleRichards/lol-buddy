import boto3
import json
import logging
from boto3.dynamodb.conditions import Key
from custom_encoder import CustomEncoder

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = None

get_method = "GET"
favourites_path = "/favourites"


def lambda_handler(event, context):
    logger.info(event)
    http_method = event["httpMethod"]
    path = event["path"]
    email = event["queryStringParameters"]["email"]
    region = event["queryStringParameters"]["region"]
    global table
    if region == "OC1":
        table = dynamodb.Table("favourites_oce")
    elif region == "NA1":
        table = dynamodb.Table("favourites_na")
    if http_method == get_method and path == favourites_path:
        response = get_favourites(email, region)
    else:
        response = build_response(404, "Not found")
    return response


def get_favourites(email, region):
    try:
        response = table.query(KeyConditionExpression=Key("email").eq(email))
        if response["Items"]:
            return build_response(200, response["Items"])
        else:
            return build_response(404, {"message": "No favourites in" + region})
    except:
        logger.exception("An error occurred. Could not get user.")


def build_response(status_code, body=None):
    response = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
    }
    if body is not None:
        response["body"] = json.dumps(body, cls=CustomEncoder)
    return response