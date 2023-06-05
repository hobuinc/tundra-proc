#!/bin/bash

IMAGE="259232244835.dkr.ecr.us-west-2.amazonaws.com/hobulandrush-dev-pdal_runner:arm64"

UUID=$(od -x /dev/urandom | head -1 | awk '{OFS="-"; print $2$3,$4,$5,$6,$7$8$9}')
echo "uid: $UUID"
mkdir -p "./tmp/${UUID}"
docker run -t -i \
    -v `pwd`:/data \
    -v ~/.aws/:/root/.aws:ro \
    -e AWS_DEFAULT_REGION="us-west-2" \
    -e AWS_DEFAULT_PROFILE="grid" \
    -e TMPDIR=/data/tmp/${UUID} \
    -w /data \
    --entrypoint=/data/entry.sh \
    $IMAGE \
    s3://grid-dev-lidarscans/Fairbanks-A-TLS/lasz/20220520-1537-09.PIVOX1.las.gz \
    s3://grid-dev-lidarscans/Fairbanks-A-TLS/

#    s3://grid-dev-lidarscans/Fairbanks-A-TLS/rxp/20220530-0904-08.MAIN.frame.rxp.gz \
#    s3://grid-dev-lidarscans/Fairbanks-A-TLS/rxp/20221006-1504-49.GNSS2.frame.rxp.gz \ empty

#    s3://grid-dev-lidarscans/Fairbanks-A-TLS/lasz/20220522-1540-21.PIVOX2.las.gz \
#    s3://grid-dev-lidarscans/Fairbanks-A-TLS/rxp/20221009-1529-55.GNSS3.frame.rxp.gz \
#    s3://grid-dev-lidarscans/Fairbanks-A-TLS/rxp/20220928-2104-07.MAIN.frame.rxp.gz

#    s3://grid-dev-lidarscans/Fairbanks-A-TLS/rxp/20221009-1529-55.GNSS3.frame.rxp.gz


#    s3://grid-dev-lidarscans/Fairbanks-A-TLS/rxp/20220520-0304-09.MAIN.frame.rxp.gz

