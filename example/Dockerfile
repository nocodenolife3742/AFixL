FROM afixl-env:latest

COPY ./src ./build.sh /src/
COPY ./eval /eval
RUN apt-get update && apt-get upgrade -y && apt autoremove -y