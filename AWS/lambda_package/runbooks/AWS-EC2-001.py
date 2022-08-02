"""
Remediate Prisma Policy:

AWS:EC2-001 EBS Volume Does Not Have Recent Snapshot

Description:

Elastic block store (EBS) volumes have no snapshots in recent, 15-day history. These are needed to retain
critical system data, security logs, and system state.

EBS volume snapshots are an important tool to record system state, security log data, and critical system
data at various points in your EC2 instance lifecycle. Snapshots provide point-in-time recovery and review
capability that is necessary for many operational and security practices.

Required Permissions:

- ec2:CreateSnapshot
- ec2:DescribeSnapshots

Sample IAM Policy:

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "EC2Permissions",
            "Effect": "Allow",
            "Action": [
                "ec2:CreateSnapshot",
                "ec2:DescribeSnapshots"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
"""

import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from datetime import date

# Options:
#
# Snapshot age in days
# 
snapshot_age = 15


def remediate(session, alert, lambda_context):
  """
  Main Function invoked by index_prisma.py
  """

  volume_id = alert['resource_id']
  region    = alert['region']

  ec2 = session.client('ec2', region_name=region)

  try:
    snapshot = ec2.describe_snapshots(Filters=[{ 'Name': 'volume-id', 'Values': [ volume_id ] }])['Snapshots']
  except ClientError as e:
    print(e.response['Error']['Message'])
    return

  if len(snapshot) > 0:
    snap_date = snapshot[0]['StartTime'].date()    # Snapshot creation date
    today = date.today()                           # Today's date
    delta = today - snap_date                      # The diff

    snapshot_needed = delta.days >= snapshot_age
  else:
    snapshot_needed = True

  if snapshot_needed:
    response = new_ebs_snapshot(ec2, volume_id)

  return


def new_ebs_snapshot(ec2, volume_id):
  """
  Create a new EBS Volume Snapshot
  """

  try:
    response = ec2.create_snapshot(VolumeId=volume_id, Description='Autoremediate snapshot')
    snapshot_id = response['SnapshotId']

    print(f'New snapshot {snapshot_id} created for EBS Volume {volume_id}.')

  except ClientError as e:
    print(e.response['Error']['Message'])

  return

