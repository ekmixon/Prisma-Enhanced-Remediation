"""
Remediate Prisma Policy:

AWS:ELB-015 Application Load Balancer (elbv2) Access Log Enabled

Description:

Ensure that your AWS Application Elastic Load Balancers has access logging to analyze traffic patterns
and identify and troubleshoot security issues.

Required Permissions:

- elasticloadbalancing:DescribeLoadBalancerAttributes
- elasticloadbalancing:DescribeLoadBalancers
- elasticloadbalancing:ModifyLoadBalancerAttributes
- s3:CreateBucket
- s3:PutBucketPolicy
- s3:PutObject

Sample IAM Policy:

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ELBPermissions",
      "Action": [
        "elasticloadbalancing:DescribeLoadBalancerAttributes",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:ModifyLoadBalancerAttributes"
      ],
      "Effect": "Allow",
      "Resource": "*"
    },
    {
      "Sid": "S3Permissions",
      "Action": [
        "s3:CreateBucket",
        "s3:PutBucketPolicy",
        "s3:PutObject"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
"""

import json
import boto3
from botocore.exceptions import ClientError


def remediate(session, alert, lambda_context):
  """
  Main Function invoked by index_prisma.py
  """

  arn      = alert['resource_id']
  elb_name = arn.split('/')[2]
  region   = alert['region']

  elbv2 = session.client('elbv2', region_name=region)
  s3 = session.client('s3', region_name=region)

  try:
    elb = elbv2.describe_load_balancers(Names=[ elb_name ])['LoadBalancers']
  except ClientError as e:
    print(e.response['Error']['Message'])
    return

  try:
    elb_arn = elb[0]['LoadBalancerArn']
  except (KeyError, IndexError):
    print(f'Error: Unable to find the ARN for Application ELB {elb_name}.')
    return

  else:
    account_id = elb_arn.split(':')[4]

  try:
    attribs = elbv2.describe_load_balancer_attributes(LoadBalancerArn=elb_arn)['Attributes']
  except ClientError as e:
    print(e.response['Error']['Message'])
    return

  logging = 'none'

  for attrib in attribs:
    if attrib['Key'] == 'access_logs.s3.enabled':
      logging = attrib['Value']

  if logging != 'true':

    bucket_name = new_s3_bucket(s3, elb_name, account_id, region)

    if bucket_name != 'fail':
      result = enable_access_log(elbv2, elb_arn, elb_name, bucket_name, region)

  return


def enable_access_log(elbv2, elb_arn, elb_name, bucket_name, region):
  """
  Enable ELB Application (elbv2) Access Log
  """

  try:
    result = elbv2.modify_load_balancer_attributes(
      LoadBalancerArn = elb_arn,
      Attributes = [
        {
          'Key': 'access_logs.s3.enabled',
          'Value': 'true'
        },
        {
          'Key': 'access_logs.s3.bucket',
          'Value': bucket_name
        },
        {
          'Key': 'access_logs.s3.prefix',
          'Value': elb_name
        }
      ]
    )
  except ClientError as e:
    if 'Access Denied' in e.response['Error']['Message']:
      print(f'Access Denied: Check the AWS ELB Account Id for the {region} region.')
    else:
      print(e.response['Error']['Message'])

  else:
    print(f'Enabled Access Log for Application ELB {elb_name}.')

  return


def new_s3_bucket(s3, elb_name, account_id, region):
  """
  Create new S3 Bucket
  """

  bucket_name = f'elbv2logs-{account_id}-{region}'

  try:
    if region == 'us-east-1':
      result = s3.create_bucket(
        ACL = 'private',
        Bucket = bucket_name
      )
    else:
      result = s3.create_bucket(
        ACL = 'private',
        Bucket = bucket_name,
        CreateBucketConfiguration = {'LocationConstraint': region}
      )

    print(f'New S3 bucket created: {bucket_name}')

  except ClientError as e:
    if e.response['Error']['Code'] == 'BucketAlreadyExists':
      print(f'Using existing S3 bucket: {bucket_name}')
    elif e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
      print(f'Using already owned and existing S3 bucket: {bucket_name}')
    else:
      print(e.response['Error']['Message'])
      return 'fail'

  # Create ELB folder/ prefix
  try:
    result = s3.put_object(Bucket = bucket_name, Key=f'{elb_name}/')
  except ClientError as e:
    print(e.response['Error']['Message'])
    return 'fail'

  # Create ELB logging policy
  try:
    result = s3.put_bucket_policy(
      Bucket = bucket_name,
      Policy = json.dumps(BucketTemplate.BucketPolicy(bucket_name, account_id, region))
    )
  except ClientError as e:
    if 'Invalid principal' in e.response['Error']['Message']:
      print(
          f'Invalid principal: Check the AWS ELB Account Id for the {region} region.'
      )
    else:
      print(e.response['Error']['Message'])
    return 'fail'

  return bucket_name


class BucketTemplate():

  def BucketPolicy(self, account_id, region):

    elb_account_id = '123456789012'

    # Reference:
    # https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/enable-access-logs.html

    if region == 'ap-northeast-1':
      elb_account_id = '582318560864'
    elif region == 'ap-northeast-2':
      elb_account_id = '600734575887'
    elif region == 'ap-northeast-3':
      elb_account_id = '383597477331'
    elif region == 'ap-south-1':
      elb_account_id = '718504428378'
    elif region == 'ap-southeast-1':
      elb_account_id = '114774131450'
    elif region == 'ap-southeast-2':
      elb_account_id = '783225319266'
    elif region == 'ca-central-1':
      elb_account_id = '985666609251'
    elif region == 'eu-central-1':
      elb_account_id = '054676820928'
    elif region == 'eu-west-1':
      elb_account_id = '156460612806'
    elif region == 'eu-west-2':
      elb_account_id = '652711504416'
    elif region == 'eu-west-3':
      elb_account_id = '009996457667'
    elif region == 'sa-east-1':
      elb_account_id = '507241528517'
    elif region == 'us-east-1':
      elb_account_id = '127311923021'
    elif region == 'us-east-2':
      elb_account_id = '033677994240'
    elif region == 'us-west-1':
      elb_account_id = '027434742980'
    elif region == 'us-west-2':
      elb_account_id = '797873946194'
    return {
        'Version':
        '2012-10-17',
        'Statement': [
            {
                'Sid': 'ELBLoggingPolicy',
                'Effect': 'Allow',
                'Principal': {
                    'AWS': f'arn:aws:iam::{elb_account_id}:root'
                },
                'Action': 's3:PutObject',
                'Resource': f'arn:aws:s3:::{self}/*/AWSLogs/{account_id}/*',
            },
            {
                'Effect': 'Allow',
                'Principal': {
                    'Service': 'delivery.logs.amazonaws.com'
                },
                'Action': 's3:PutObject',
                'Resource': f'arn:aws:s3:::{self}/*/AWSLogs/{account_id}/*',
                'Condition': {
                    'StringEquals': {
                        's3:x-amz-acl': 'bucket-owner-full-control'
                    }
                },
            },
            {
                'Effect': 'Allow',
                'Principal': {
                    'Service': 'delivery.logs.amazonaws.com'
                },
                'Action': 's3:GetBucketAcl',
                'Resource': f'arn:aws:s3:::{self}',
            },
        ],
    }

