# Python runtime as a base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any necessary dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask will run on
EXPOSE 8080

# Define environment variable to run the app in production
ENV FLASK_ENV=production

# Run the Gunicorn server instead of Flask's built-in server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
