# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY prep_bot.py .

# Expose port 5000 to the outside world
EXPOSE 5000

# Command to run the script
CMD ["python", "prep_bot.py"]