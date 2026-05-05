#!/bin/bash
docker build -t clause-extractor . && \
docker run -d \
  --name clause-extractor \
  --env-file .env \
  -p 6363:6363 \
  -v clause-extractor-data:/data \
  clause-extractor
