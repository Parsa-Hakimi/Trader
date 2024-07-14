FROM docker.repos.balad.ir/python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip3 config set global.index-url https://repos.balad.ir/artifactory/api/pypi/pypi-public/simple/
RUN pip3 install -r requirements.txt --no-cache-dir

COPY . .

ENTRYPOINT ["/app/docker-entrypoint.sh"]
