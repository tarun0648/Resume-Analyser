import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment_setup():
    """Test if all environment variables are set up correctly"""
    print("🔍 Testing environment setup...")
    
    required_env_vars = [
        'CLAUDE_API_KEY',
        'FIREBASE_PROJECT_ID',
        'FIREBASE_PRIVATE_KEY',
        'FIREBASE_CLIENT_EMAIL',
        'FIREBASE_STORAGE_BUCKET'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            if var == 'CLAUDE_API_KEY':
                if not value.startswith('sk-ant-'):
                    print(f"   ⚠️  {var} format seems incorrect (should start with 'sk-ant-')")
                else:
                    print(f"   ✅ {var} format looks correct")
            else:
                print(f"   ✅ {var} is set")
    
    if missing_vars:
        print(f"   ❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("   ✅ All environment variables are set")
    return True

def test_claude_http_client():
    """Test the HTTP Claude client"""
    print("\n🔍 Testing Claude HTTP client...")
    
    try:
        api_key = os.getenv('CLAUDE_API_KEY')
        if not api_key:
            print("   ❌ CLAUDE_API_KEY not found")
            return False
        
        # Import our HTTP client
        from resume_extractor_cl import ClaudeHTTPClient
        
        client = ClaudeHTTPClient(api_key)
        print("   ✅ Claude HTTP client initialized")
        
        # Test with a simple message
        response = client.messages_create(
            model="claude-3-opus-20240229",
            max_tokens=10,
            messages=[
                {
                    "role": "user",
                    "content": "Say hello"
                }
            ]
        )
        
        print("   ✅ Claude API call successful!")
        print(f"   Response: {response.content[0].text[:50]}...")
        return True
        
    except Exception as e:
        print(f"   ❌ Claude client test failed: {e}")
        return False

def test_imports():
    """Test if all required modules can be imported"""
    print("\n🔍 Testing imports...")
    
    modules_to_test = [
        ('flask', 'Flask'),
        ('firebase_admin', 'Firebase Admin'),
        ('PyPDF2', 'PyPDF2'),
        ('requests', 'Requests'),
        ('json', 'JSON'),
        ('os', 'OS'),
        ('dotenv', 'Python DotEnv')
    ]
    
    failed_imports = []
    for module, name in modules_to_test:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError as e:
            print(f"   ❌ {name}: {e}")
            failed_imports.append(name)
    
    # Test our custom modules
    try:
        from resume_extractor_cl import get_claude_client, process_resume_file
        print("   ✅ Resume Extractor")
    except ImportError as e:
        print(f"   ❌ Resume Extractor: {e}")
        failed_imports.append("Resume Extractor")
    
    try:
        from resume_summarizer import compare_resume_with_job
        print("   ✅ Resume Summarizer")
    except ImportError as e:
        print(f"   ❌ Resume Summarizer: {e}")
        failed_imports.append("Resume Summarizer")
    
    try:
        from config import CLAUDE_API_KEY, FIREBASE_STORAGE_BUCKET
        print("   ✅ Config")
    except ImportError as e:
        print(f"   ❌ Config: {e}")
        failed_imports.append("Config")
    
    if failed_imports:
        print(f"   ❌ Failed imports: {', '.join(failed_imports)}")
        return False
    
    print("   ✅ All imports successful")
    return True

def test_firebase_setup():
    """Test Firebase setup"""
    print("\n🔍 Testing Firebase setup...")
    
    try:
        # Check if serviceAccountKey.json exists
        if not os.path.exists('serviceAccountKey.json'):
            print("   ❌ serviceAccountKey.json not found")
            return False
        
        print("   ✅ serviceAccountKey.json found")
        
        # Try to load and validate the key
        with open('serviceAccountKey.json', 'r') as f:
            key_data = json.load(f)
        
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in key_data]
        
        if missing_fields:
            print(f"   ❌ Missing fields in serviceAccountKey.json: {', '.join(missing_fields)}")
            return False
        
        print("   ✅ serviceAccountKey.json is valid")
        return True
        
    except Exception as e:
        print(f"   ❌ Firebase setup test failed: {e}")
        return False

def test_directories():
    """Test if required directories exist"""
    print("\n🔍 Testing directories...")
    
    required_dirs = ['resumes', 'logs']
    
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            print(f"   ⚠️  Creating missing directory: {dir_name}")
            os.makedirs(dir_name, exist_ok=True)
        print(f"   ✅ {dir_name} directory exists")
    
    return True

def test_flask_app():
    """Test if Flask app can be initialized"""
    print("\n🔍 Testing Flask app initialization...")
    
    try:
        from main import app
        print("   ✅ Flask app imported successfully")
        
        # Test if app can be configured
        with app.app_context():
            print("   ✅ Flask app context works")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Flask app test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 FINAL RESUME PROCESSOR TEST")
    print("=" * 50)
    
    tests = [
        ("Environment Setup", test_environment_setup),
        ("Import Tests", test_imports),
        ("Directory Setup", test_directories),
        ("Firebase Setup", test_firebase_setup),
        ("Claude HTTP Client", test_claude_http_client),
        ("Flask App", test_flask_app)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 FINAL RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("Your resume processor is ready to run!")
        print("\nNext steps:")
        print("1. Run: python main.py")
        print("2. Open your browser to the frontend")
        print("3. Upload a resume PDF to test")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed.")
        print("Please fix the issues above before running the application.")
        return 1

if __name__ == "__main__":
    sys.exit(main())