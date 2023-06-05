#!/bin/bash

echo "hello from docker"

echo "new entry"


if [ -n "$AWS_BATCH_JOB_ID" ]
then
echo "fetching work package"

aws s3 cp s3://grid-dev-lidarscans/Fairbanks-A-TLS/hobu.zip .
unzip hobu.zip
fi




python submit.py "$1" "$2"


