FROM aflplusplus/aflplusplus:latest

# Update and upgrade the base image
RUN apt update && apt upgrade -y && apt autoremove -y

# Make directory for executables, source code, and evaluation inputs
RUN mkdir /exe
RUN mkdir /src
RUN mkdir /eval
