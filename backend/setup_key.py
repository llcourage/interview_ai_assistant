"""
Quick setup script - Generate Encryption Key
"""
from cryptography.fernet import Fernet

def generate_encryption_key():
    """Generate Fernet encryption key"""
    key = Fernet.generate_key()
    return key.decode()

if __name__ == "__main__":
    print("=" * 60)
    print("🔐 Desktop AI - Encryption Key Generator")
    print("=" * 60)
    print()
    
    key = generate_encryption_key()
    
    print("✅ Encryption key generated:")
    print()
    print(f"ENCRYPTION_KEY={key}")
    print()
    print("⚠️  Please add this key to .env file")
    print("⚠️  Please keep this key safe, if lost all user API Keys will be unable to decrypt")
    print()
    print("=" * 60)








