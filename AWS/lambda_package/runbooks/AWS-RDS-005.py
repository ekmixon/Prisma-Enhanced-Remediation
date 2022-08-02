"""
Remediate Prisma Policy:

AWS:RDS-005 RDS Database Publicly Accessible

Description:

RDS database instances should not be made accessible to the public internet, outside of your VPC. This is
dangerous, as RDS databases should normally be privately accessible only from within your VPC.

Required Permissions:

- rds:DescribeDBInstances
- rds:ModifyDBInstance

Sample IAM Policy:

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RDSPermissions",
      "Action": [
        "rds:DescribeDBInstances",
        "rds:ModifyDBInstance"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
"""

import boto3
from botocore.exceptions import ClientError


def remediate(session, alert, lambda_context):
  """
  Main Function invoked by index_prisma.py
  """

  resource_id = alert['resource_id']
  region      = alert['region']

  rds = session.client('rds', region_name=region)

  try:
    db_instance = rds.describe_db_instances(
      Filters = [
        {
          'Name': 'dbi-resource-id',
          'Values': [ resource_id ]
        }
      ]
    )['DBInstances']

  except ClientError as e:
    print(e.response['Error']['Message'])
    return

  try:
    public = db_instance[0]['PubliclyAccessible']
  except (KeyError, IndexError):
    public = False

  if public: 

    instance_id = db_instance[0]['DBInstanceIdentifier']

    try:
      rds.modify_db_instance(
        DBInstanceIdentifier = instance_id,
        PubliclyAccessible = False
      )
    except ClientError as e:
      print(e.response['Error']['Message'])
      return

    else:
      print(f'Removed public attribute from RDS instance {instance_id}.')

  return

