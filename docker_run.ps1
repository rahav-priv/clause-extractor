docker build -t clause-extractor .
if ($LASTEXITCODE -eq 0) {
    docker run -d `
      --name clause-extractor `
      --env-file .env `
      -p 6363:6363 `
      -v "$PWD/data:/data" `
      clause-extractor
}
