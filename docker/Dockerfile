FROM aflplusplus/aflplusplus:latest

# Install dependencies
RUN apt update && apt upgrade -y && apt autoremove -y

# Create essential directories
RUN mkdir -p /out /src

# Set the working directory
WORKDIR /src