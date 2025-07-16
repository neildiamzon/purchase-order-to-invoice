FROM python:3.10-slim

# Install Java for tabula-py
RUN apt-get update && apt-get install -y default-jre gcc && apt-get clean

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy your project files (adjust path as needed)
COPY flaskr/ ./

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port for app
EXPOSE 5000

# Run the app using Waitress
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "app:app"]
