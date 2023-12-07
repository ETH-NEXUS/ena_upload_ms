FROM python:3.11-bookworm

# Optimise python and debian in docker
ENV PYTHONUNBUFFERED 1
ENV PIP_BREAK_SYSTEM_PACKAGES 1
ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV DEBIAN_FRONTEND noninteractive

# Install the webin dependencies
# RUN wget http://www.mirbsd.org/~tg/Debs/sources.txt/wtf-bookworm.sources
# RUN mkdir -p /etc/apt/sources.list.d
# RUN mv wtf-bookworm.sources /etc/apt/sources.list.d/
# RUN apt-get update && apt-get install -y openjdk-8-jdk
RUN mkdir -p /etc/apt/keyrings
RUN wget -O - https://packages.adoptium.net/artifactory/api/gpg/key/public | tee /etc/apt/keyrings/adoptium.asc
RUN echo "deb [signed-by=/etc/apt/keyrings/adoptium.asc] https://packages.adoptium.net/artifactory/deb $(awk -F= '/^VERSION_CODENAME/{print$2}' /etc/os-release) main" | tee /etc/apt/sources.list.d/adoptium.list
RUN apt-get update && apt-get install -y temurin-8-jdk
RUN cd /opt && \
    wget https://github.com/enasequence/webin-cli/releases/download/6.7.2/webin-cli-6.7.2.jar && \
    mv webin-cli-6.7.2.jar webin-cli.jar
RUN apt-get install -y rubygems
RUN gem install aspera-cli
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Global python requirements
COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

# Set the git information
ENV GIT_VERSION=${GIT_VERSION}
ENV GIT_BRANCH=${GIT_BRANCH}
ENV GIT_LASTCOMMITDATE=${GIT_LASTCOMMITDATE}

# Copy the app to the image
COPY ./app /app

# Set working directory
WORKDIR /app

# Set the entrypoint
ENTRYPOINT [ "/app/entrypoint.sh" ]