#!/bin/bash

# Resume Processor Deployment Script
# This script helps set up and deploy the resume processor application

set -e

echo "🚀 Resume Processor Deployment Script"
echo "====================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required commands exist
check_requirements() {
    print_status "Checking requirements..."
    
    local missing_commands=()
    
    if ! command -v python3 &> /dev/null; then
        missing_commands+=("python3")
    fi
    
    if ! command -v pip3 &> /dev/null; then
        missing_commands+=("pip3")
    fi
    
    if [ ${#missing_commands[@]} -ne 0 ]; then
        print_error "Missing required commands: ${missing_commands[*]}"
        print_error "Please install them before running this script."
        exit 1
    fi
    
    print_status "All requirements satisfied ✓"
}

# Setup virtual environment
setup_venv() {
    print_status "Setting up virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Virtual environment created ✓"
    else
        print_warning "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    print_status "Virtual environment activated ✓"
}

# Install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_status "Dependencies installed ✓"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# Setup environment variables
setup_environment() {
    print_status "Setting up environment variables..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_warning "Copied .env.example to .env"
            print_warning "Please edit .env file with your actual configuration values"
        else
            print_error ".env.example not found"
            exit 1
        fi
    else
        print_warning ".env file already exists"
    fi
}

# Check Firebase service account key
check_firebase_key() {
    print_status "Checking Firebase service account key..."
    
    if [ ! -f "serviceAccountKey.json" ]; then
        print_error "serviceAccountKey.json not found"
        print_error "Please download your Firebase service account key and save it as serviceAccountKey.json"
        exit 1
    else
        print_status "Firebase service account key found ✓"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p resumes
    mkdir -p logs
    
    print_status "Directories created ✓"
}

# Run tests
run_tests() {
    print_status "Running basic tests..."
    
    # Test Python imports
    python3 -c "
import sys
try:
    import flask
    import firebase_admin
    import anthropic
    import PyPDF2
    print('✓ All required packages imported successfully')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
"
    
    print_status "Tests passed ✓"
}

# Start application
start_application() {
    print_status "Starting application..."
    
    echo ""
    echo "🎉 Setup complete! Your resume processor is ready to run."
    echo ""
    echo "To start the application:"
    echo "1. Activate virtual environment: source venv/bin/activate"
    echo "2. Run the application: python main.py"
    echo ""
    echo "Or use Docker:"
    echo "docker-compose up --build"
    echo ""
    echo "Don't forget to:"
    echo "- Update your .env file with actual values"
    echo "- Ensure your Firebase project is properly configured"
    echo "- Update the frontend API_BASE_URL if needed"
    echo ""
    
    read -p "Would you like to start the application now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Starting Flask application..."
        python main.py
    fi
}

# Docker deployment
deploy_docker() {
    print_status "Deploying with Docker..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose not found. Please install Docker Compose first."
        exit 1
    fi
    
    # Build and start containers
    docker-compose up --build -d
    
    print_status "Docker containers started ✓"
    print_status "Application is running at http://localhost"
    print_status "API is available at http://localhost:5000"
    
    # Show logs
    echo ""
    echo "To view logs:"
    echo "docker-compose logs -f"
    echo ""
    echo "To stop the application:"
    echo "docker-compose down"
}

# Main deployment function
main() {
    echo "Select deployment option:"
    echo "1. Local development setup"
    echo "2. Docker deployment"
    echo "3. Full setup and start"
    echo ""
    read -p "Enter your choice (1-3): " choice
    
    case $choice in
        1)
            check_requirements
            setup_venv
            install_dependencies
            setup_environment
            check_firebase_key
            create_directories
            run_tests
            echo ""
            print_status "Local development setup complete!"
            print_warning "Please update your .env file before starting the application"
            ;;
        2)
            check_firebase_key
            deploy_docker
            ;;
        3)
            check_requirements
            setup_venv
            install_dependencies
            setup_environment
            check_firebase_key
            create_directories
            run_tests
            start_application
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"