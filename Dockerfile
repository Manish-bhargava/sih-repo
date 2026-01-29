# Use a Node.js base image
FROM node:20

# Install Python and dependencies for the AI server
RUN apt-get update && apt-get install -y python3 python3-pip

# Set working directory
WORKDIR /app

# Copy the entire repository
COPY . .

# 1. Install Backend dependencies
RUN cd backend && npm install

# 2. Build the Dashboard (Next.js)
# Ensure next.config.ts has { output: 'export' }
RUN cd live-dashboard && npm install && npm run build

# 3. Install Python dependencies for the AI Server
RUN pip3 install --no-cache-dir flask xgboost pandas numpy scikit-learn --break-system-packages

# Expose the backend port
EXPOSE 5001

# Start script: Runs the Node.js backend and Python AI server simultaneously
CMD python3 backend/app.py & node backend/server.js