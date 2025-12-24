ARG BUILD_FROM
FROM $BUILD_FROM

# Install required packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash

# Create app directory
WORKDIR /app

# Copy custom component
COPY custom_components/ /usr/src/app/custom_components/

# Copy run script
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]