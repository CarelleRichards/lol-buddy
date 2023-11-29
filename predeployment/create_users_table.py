import boto3
table_name = "users"
partition_key = "email"


# Creates users table in DynamoDB
def create_table(dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    "AttributeName": partition_key,
                    "KeyType": "HASH"  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    "AttributeName": partition_key,
                    "AttributeType": "S"
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 10,
                "WriteCapacityUnits": 10
            }
        )
        print(table.table_status + " " + table_name + " table...")
        table.wait_until_exists()
        print(table_name + " table created.")


# Deletes users table in DynamoDB
def delete_table(dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    table.delete()
    print(table.table_status + " existing " + table_name + " table...")
    table.wait_until_not_exists()
    print(table_name + " table deleted.")


if __name__ == '__main__':
    try:
        delete_table()
    except:
        print("Couldn't delete " + table_name + " table or it doesn't exist.")
    try:
        create_table()
    except:
        print("Couldn't create " + table_name + " table. Check AWS credentials.")
