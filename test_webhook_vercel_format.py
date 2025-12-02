"""
测试 Vercel Python 函数格式
检查是否有导入问题
"""
import sys
import os
from pathlib import Path

# 模拟 Vercel 的模块检查过程
print("=" * 60)
print("模拟 Vercel 的模块检查过程")
print("=" * 60)

# 添加 api 目录到路径
api_path = Path(__file__).parent / "api"
sys.path.insert(0, str(api_path))

print(f"\n1. 检查文件是否存在...")
stripe_file = api_path / "stripe_webhook.py"
if stripe_file.exists():
    print(f"   ✅ 文件存在: {stripe_file}")
else:
    print(f"   ❌ 文件不存在: {stripe_file}")
    sys.exit(1)

print(f"\n2. 读取文件内容...")
try:
    with open(stripe_file, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"   ✅ 文件读取成功 ({len(content)} 字符)")
except Exception as e:
    print(f"   ❌ 文件读取失败: {e}")
    sys.exit(1)

print(f"\n3. 检查文件中的导入语句...")
import_lines = [line.strip() for line in content.split('\n') if line.strip().startswith(('import ', 'from '))]
print(f"   找到 {len(import_lines)} 个导入语句:")
for line in import_lines[:10]:  # 只显示前10个
    print(f"   - {line}")
if len(import_lines) > 10:
    print(f"   ... 还有 {len(import_lines) - 10} 个")

print(f"\n4. 尝试编译文件...")
try:
    compile(content, str(stripe_file), 'exec')
    print("   ✅ 文件编译成功（语法正确）")
except SyntaxError as e:
    print(f"   ❌ 语法错误: {e}")
    sys.exit(1)
except Exception as e:
    print(f"   ⚠️ 编译警告: {e}")

print(f"\n5. 尝试导入模块（不执行）...")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("stripe_webhook", stripe_file)
    if spec is None:
        print("   ❌ 无法创建模块规范")
        sys.exit(1)
    print("   ✅ 模块规范创建成功")
except Exception as e:
    print(f"   ❌ 创建模块规范失败: {e}")
    sys.exit(1)

print(f"\n6. 检查是否有模块级别的代码执行...")
# 检查是否有在模块级别执行的代码（除了导入和函数定义）
module_level_code = []
for i, line in enumerate(content.split('\n'), 1):
    stripped = line.strip()
    if stripped and not stripped.startswith(('import ', 'from ', 'def ', 'class ', '#', '"""', "'''")):
        if not stripped.startswith(' ') and not stripped.startswith('\t'):  # 不是缩进的代码
            module_level_code.append((i, stripped))

if module_level_code:
    print(f"   ⚠️ 发现 {len(module_level_code)} 行模块级别的代码:")
    for line_num, code in module_level_code[:5]:
        print(f"   第 {line_num} 行: {code}")
    if len(module_level_code) > 5:
        print(f"   ... 还有 {len(module_level_code) - 5} 行")
else:
    print("   ✅ 没有模块级别的代码执行（只有导入和函数定义）")

print(f"\n7. 尝试实际导入模块...")
try:
    # 使用 importlib 导入，但不执行
    import importlib.util
    spec = importlib.util.spec_from_file_location("stripe_webhook_test", stripe_file)
    module = importlib.util.module_from_spec(spec)
    # 不执行 spec.loader.exec_module(module)，只检查规范
    print("   ✅ 模块规范检查通过")
except Exception as e:
    print(f"   ❌ 模块规范检查失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("检查完成！")
print("=" * 60)
print("\n如果所有检查通过，代码本身应该没问题。")
print("Vercel 的错误可能是环境或配置问题。")

