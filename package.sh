#!/bin/bash

IMAGE="259232244835.dkr.ecr.us-west-2.amazonaws.com/hobulandrush-dev-pdal_runner:arm64"

PACKAGE="s3://grid-dev-lidarscans/Fairbanks-A-TLS/hobu.zip"

rm hobu.zip
rm -rf tmp

zip hobu.zip -r .

aws s3 cp hobu.zip $PACKAGE

