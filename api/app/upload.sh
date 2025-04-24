#!/usr/bin/env bash

echo "Starting uploader..."
sleep 10
while true; do python manage.py upload; sleep 10; done


