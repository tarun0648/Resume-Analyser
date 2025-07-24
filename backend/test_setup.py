#!/usr/bin/env python3
"""
Test script to verify the resume processor setup
"""

import os
import sys
import json
from pathlib import Path

def test_imports():
    """Test if all required packages can be imported"""
    print("🔍 Testing imports...")
    
    required_packages = [
        'flask',
        'firebase_admin',
        'anthropic',
        'PyPDF2',
        'python-dotenv'
    ]
    
    failed_imports = []
    
    for package in required_packages:
        try:
            if package == 'python-dotenv':
                import dotenv
            else:
                __import__(package)
            print(f"  ✓ {package}")
        except ImportError as e:
            print(f"  ✗ {package}: {e}")
            failed_imports.append(package)
    
    if failed_imports:
        print(f"\n❌ Failed imports: {', '.join(failed_imports)}")
        return False
    else:
        print("✅ All imports successful!")
        return True

def test_environment():
    """Test environment configuration"""
    print("\n🔍 Testing environment configuration...")
    
    # Check .env file
    env_file = Path('.env')
    if not env_file.exists():
        print("  ✗ .env file not found")
        return False
    print("  ✓ .env file exists")
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        required_env_vars = [
            'CLAUDE_API_KEY',
            'FIREBASE_PROJECT_ID',
            'FIREBASE_PRIVATE_KEY',
            'FIREBASE_CLIENT_EMAIL',
            'FIREBASE_STORAGE_BUCKET'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
            else:
                print(f"  ✓ {var} is set")
        
        if missing_vars:
            print(f"  ✗ Missing environment variables: {', '.join(missing_vars)}")
            return False
        
    except Exception as e:
        print(f"  ✗ Error loading environment: {e}")
        return False
    
    print("✅ Environment configuration OK!")
    return True

def test_firebase_key():
    """Test Firebase service account key"""
    print("\n🔍 Testing Firebase service account key...")
    
    key_file = Path('serviceAccountKey.json')
    if not key_file.exists():
        print("  ✗ serviceAccountKey.json not found")
        return False
    
    try:
        with open(key_file, 'r') as f:
            key_data = json.load(f)
        
        required_fields = [
            'type', 'project_id', 'private_key_id', 'private_key',
            'client_email', 'client_id', 'auth_uri', 'token_uri'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in key_data:
                missing_fields.append(field)
            else:
                print(f"  ✓ {field} present")
        
        if missing_fields:
            print(f"  ✗ Missing fields in service account key: {', '.join(missing_fields)}")
            return False
        
    except json.JSONDecodeError:
        print("  ✗ Invalid JSON in serviceAccountKey.json")
        return False
    except Exception as e:
        print(f"  ✗ Error reading service account key: {e}")
        return False
    
    print("✅ Firebase service account key OK!")
    return True

def test_directories():
    """Test required directories"""
    print("\n🔍 Testing directories...")
    
    required_dirs = ['resumes']
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            print(f"  ⚠ Creating directory: {dir_name}")
            dir_path.mkdir(exist_ok=True)
        print(f"  ✓ {dir_name} directory exists")
    
    print("✅ Directories OK!")
    return True

def test_claude_api():
    """Test Claude API connectivity"""
    print("\n🔍 Testing Claude API connectivity...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('CLAUDE_API_KEY')
        if not api_key:
            print("  ✗ CLAUDE_API_KEY not found in environment")
            return False
        
        # Test API key format
        if not api_key.startswith('sk-ant-'):
            print("  ✗ Claude API key doesn't match expected format")
            return False
        
        print("  ✓ Claude API key format appears valid")
        
        # Try to import and initialize Claude client
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        print("  ✓ Claude client initialized successfully")
        
        # Note: We don't make an actual API call in tests to avoid charges
        print("  ⚠ Skipping actual API call to avoid charges")
        
    except Exception as e:
        print(f"  ✗ Error testing Claude API: {e}")
        return False
    
    print("✅ Claude API setup OK!")
    return True

def test_app_structure():
    """Test application file structure"""
    print("\n🔍 Testing application structure...")
    
    required_files = [
        'main.py',
        'config.py',
        'resume_extractor_cl.py',
        'resume_summarizer.py',
        'resume_questions.py',
        'requirements.txt',
        'index.html'
    ]
    
    missing_files = []
    for file_name in required_files:
        if not Path(file_name).exists():
            missing_files.append(file_name)
        else:
            print(f"  ✓ {file_name}")
    
    if missing_files:
        print(f"  ✗ Missing files: {', '.join(missing_files)}")
        return False
    
    print("✅ Application structure OK!")
    return True

def main():
    """Run all tests"""
    print("🧪 Resume Processor Setup Test")
    print("==============================")
    
    tests = [
        test_imports,
        test_environment,
        test_firebase_key,
        test_directories,
        test_claude_api,
        test_app_structure
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "="*50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Run: python main.py")
        print("2. Open index.html in a browser")
        print("3. Upload a resume PDF to test the system")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())