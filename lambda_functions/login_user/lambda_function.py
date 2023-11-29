import boto3
import json
import logging
from boto3.dynamodb.conditions import Key, Attr
from custom_encoder import CustomEncoder

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("users")

get_method = "GET"
login_path = "/login"


def lambda_handler(event, context):
    logger.info(event)
    http_method = event["httpMethod"]
    path = event["path"]

    if http_method == get_method and path == login_path:
        email = event["queryStringParameters"]["email"]
        password = event["queryStringParameters"]["password"]
        response = get_user(email, password)
    else:
        response = build_response(404, "Not found")
    return response


def get_user(email, password):
    try:
        response = table.query(
            KeyConditionExpression=Key("email").eq(email),
            FilterExpression=Attr("password").eq(password)
        )
        if response["Items"]:
            return build_response(200, response["Items"])
        else:
            return build_response(404, {"message": "Email or password is invalid"})
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
