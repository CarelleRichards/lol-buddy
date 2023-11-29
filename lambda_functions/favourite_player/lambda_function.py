import boto3
import json
import logging
from custom_encoder import CustomEncoder
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = None

get_method = "GET"
delete_method = "DELETE"
post_method = "POST"
favourite_path = "/favourite"


def lambda_handler(event, context):
    logger.info(event)
    http_method = event["httpMethod"]
    path = event["path"]
    region = event["queryStringParameters"]["region"]
    global table
    if region == "OC1":
        table = dynamodb.Table("favourites_oce")
    elif region == "NA1":
        table = dynamodb.Table("favourites_na")
    if http_method == post_method and path == favourite_path:
        response = post_favourite(json.loads(event["body"]))
    elif http_method == delete_method and path == favourite_path:
        response = delete_favourite(json.loads(event["body"]))
    elif http_method == get_method and path == favourite_path:
        response = get_favourite(json.loads(event["body"]))
    else:
        response = build_response(404, "Not found")
    return response


def get_favourite(request_body):
    try:
        response = table.query(KeyConditionExpression=Key("email").eq(request_body["email"]) & Key("player_name").eq(request_body["player_name"]))
        if response["Items"]:
            return build_response(200, response["Items"])
        else:
            return build_response(404, {"message": "Can't find favourite"})
    except:
        logger.exception("An error occurred. Could not get favourite.")


def delete_favourite(request_body):
    try:
        table.delete_item(Key={"player_name": request_body["player_name"], "email": request_body["email"]})
        body = {
            "Operation": "DELTE",
            "Message": "SUCCESS",
            "Item": request_body
        }
        return build_response(200, body)
    except:
        logger.exception("An error occurred. Could not delete favourite.")


def post_favourite(request_body):
    try:
        table.put_item(Item=request_body)
        body = {
            "Operation": "SAVE",
            "Message": "SUCCESS",
            "Item": request_body
        }
        return build_response(200, body)
    except:
        logger.exception("An error occurred. Could not post favourite.")


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