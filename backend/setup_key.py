"""
快速设置脚本 - 生成 Encryption Key
"""
from cryptography.fernet import Fernet

def generate_encryption_key():
    """生成 Fernet 加密密钥"""
    key = Fernet.generate_key()
    return key.decode()

if __name__ == "__main__":
    print("=" * 60)
    print("🔐 AI Interview Assistant - 加密密钥生成器")
    print("=" * 60)
    print()
    
    key = generate_encryption_key()
    
    print("✅ 已生成加密密钥:")
    print()
    print(f"ENCRYPTION_KEY={key}")
    print()
    print("⚠️  请将此密钥添加到 .env 文件中")
    print("⚠️  请妥善保管此密钥，丢失后所有用户API Key将无法解密")
    print()
    print("=" * 60)

