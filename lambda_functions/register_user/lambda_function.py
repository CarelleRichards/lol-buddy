import boto3
import json
import logging
from boto3.dynamodb.conditions import Key
from custom_encoder import CustomEncoder

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("users")

get_method = "GET"
post_method = "POST"
register_path = "/register"


def lambda_handler(event, context):
    logger.info(event)
    http_method = event["httpMethod"]
    path = event["path"]

    if http_method == get_method and path == register_path:
        response = get_user(event["queryStringParameters"]["email"])
    elif http_method == post_method and path == register_path:
        response = post_user(json.loads(event["body"]))
    else:
        response = build_response(404, "Not found")
    return response


def get_user(email):
    try:
        response = table.query(KeyConditionExpression=Key("email").eq(email))
        if response["Items"]:
            return build_response(200, {"message": "The email already exists"})
            # return build_response(200, response["Items"])
        else:
            return build_response(404, {"message": "The email is available"})
    except:
        logger.exception("An error occurred. Could not get user.")


def post_user(request_body):
    try:
        table.put_item(Item=request_body)
        body = {
            "Operation": "SAVE",
            "Message": "SUCCESS",
            "Item": request_body
        }
        return build_response(200, body)
    except:
        logger.exception("An error occurred. Could not post user.")


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