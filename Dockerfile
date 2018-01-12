############################################################
# Dockerfile to build Python WSGI Application Containers
# Based on Ubuntu
############################################################

# Set the base image to Ubuntu
FROM  jfloff/alpine-python

# Copy the application folder inside the container
ADD . /trufflehog/

# Get pip to download and install requirements:
RUN pip install -r /trufflehog/requirements.txt

# Expose ports
EXPOSE 8080

# Set the default directory where CMD will execute
WORKDIR /trufflehog/

# Set the default command to execute
# when creating a new container
# i.e. using CherryPy to serve the application
CMD python /trufflehog/app.py