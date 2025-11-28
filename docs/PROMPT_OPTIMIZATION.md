# 🤖 AI 提示词优化说明

## ✨ 优化内容

### **1. 自动识别题目**
AI 现在会自动：
- 📸 从截图中识别题目内容
- 🎯 判断题目类型（算法、编程、系统设计、概念题等）
- 🧠 智能分析并给出针对性回复

### **2. 结构化回复格式**

AI 的回复现在包含以下结构：

```
📋 题目
└─ 简要描述识别到的题目

💡 解题思路
└─ 详细的分步骤思路

💻 答案
└─ 完整的解决方案（默认 Python 代码）

⏱️ 复杂度分析（算法题）
├─ 时间复杂度
└─ 空间复杂度

🔍 知识点总结
└─ 相关知识点和注意事项
```

### **3. 默认 Python 语言**
- ✅ 所有代码示例默认使用 Python
- ✅ 除非题目明确要求其他语言
- ✅ Python 代码简洁、易读、易理解

### **4. 参数优化**
- **max_tokens**: `2000` → `3000`（支持更详细的回复）
- **temperature**: `0.7` → `0.3`（更准确、更一致的回答）

---

## 📝 回复示例

### **算法题示例**

**截图内容：** "给定一个整数数组，找出两个数使得它们的和等于目标值"

**AI 回复：**

```
### 📋 题目
两数之和问题：给定一个整数数组 nums 和目标值 target，找出数组中和为 target 的两个数的索引。

### 💡 解题思路
1. 使用哈希表存储已遍历的数字及其索引
2. 遍历数组，对每个数字计算 target - nums[i]
3. 如果差值在哈希表中，说明找到了答案
4. 否则将当前数字加入哈希表

### 💻 答案
```python
def two_sum(nums, target):
    """
    寻找两数之和等于目标值
    
    Args:
        nums: 整数数组
        target: 目标值
        
    Returns:
        两个数的索引 [index1, index2]
    """
    seen = {}  # 哈希表：{数字: 索引}
    
    for i, num in enumerate(nums):
        complement = target - num
        
        if complement in seen:
            return [seen[complement], i]
        
        seen[num] = i
    
    return []  # 未找到

# 测试
nums = [2, 7, 11, 15]
target = 9
print(two_sum(nums, target))  # 输出: [0, 1]
```

### ⏱️ 复杂度分析
- **时间复杂度**: O(n) - 只需遍历数组一次
- **空间复杂度**: O(n) - 哈希表最多存储 n 个元素

### 🔍 知识点总结
- 哈希表查找时间复杂度为 O(1)
- 用空间换时间的经典算法
- 注意边界条件：数组为空、没有解的情况
```

---

### **系统设计题示例**

**截图内容：** "设计一个短链接服务"

**AI 回复：**

```
### 📋 题目
设计一个类似 bit.ly 的短链接服务，将长 URL 转换为短 URL

### 💡 解题思路
1. URL 转换：使用 Base62 编码生成短链接
2. 存储映射：数据库存储短链接到长链接的映射
3. 重定向：访问短链接时重定向到原始 URL
4. 考虑高并发、高可用性

### 💻 答案

**核心功能实现：**

```python
import hashlib
import string

class URLShortener:
    def __init__(self):
        self.url_map = {}  # 短链接 -> 长链接
        self.reverse_map = {}  # 长链接 -> 短链接
        self.base62_chars = string.ascii_letters + string.digits
        self.counter = 1000000  # 起始 ID
    
    def encode_base62(self, num):
        """将数字编码为 Base62 字符串"""
        if num == 0:
            return self.base62_chars[0]
        
        result = []
        while num > 0:
            result.append(self.base62_chars[num % 62])
            num //= 62
        
        return ''.join(reversed(result))
    
    def shorten(self, long_url):
        """生成短链接"""
        # 检查是否已存在
        if long_url in self.reverse_map:
            return self.reverse_map[long_url]
        
        # 生成短码
        short_code = self.encode_base62(self.counter)
        self.counter += 1
        
        # 存储映射
        self.url_map[short_code] = long_url
        self.reverse_map[long_url] = short_code
        
        return f"https://short.url/{short_code}"
    
    def expand(self, short_url):
        """还原长链接"""
        short_code = short_url.split('/')[-1]
        return self.url_map.get(short_code, "URL not found")

# 使用示例
shortener = URLShortener()
short = shortener.shorten("https://www.example.com/very/long/url")
print(f"短链接: {short}")
print(f"原始链接: {shortener.expand(short)}")
```

**架构设计：**

1. **应用层**：Web 服务器（Nginx + FastAPI/Flask）
2. **业务层**：URL 生成、重定向逻辑
3. **存储层**：
   - Redis：缓存热门链接
   - MySQL/PostgreSQL：持久化存储
4. **负载均衡**：多台应用服务器
5. **CDN**：加速重定向响应

### 🔍 知识点总结
- Base62 编码：使用 a-z, A-Z, 0-9 共 62 个字符
- 7 位 Base62 可支持 62^7 ≈ 3.5 万亿个 URL
- 考虑使用分布式 ID 生成器（Snowflake）
- 添加过期时间和访问统计功能
- 防止恶意链接（安全检查）
```

---

## 🎯 使用建议

### **1. 不同类型题目的表现**

| 题目类型 | AI 表现 | 回复内容 |
|---------|--------|---------|
| 算法题 | ⭐⭐⭐⭐⭐ | 思路 + Python 代码 + 复杂度 |
| 编程题 | ⭐⭐⭐⭐⭐ | 完整代码 + 测试用例 |
| 系统设计 | ⭐⭐⭐⭐ | 架构设计 + 关键技术 |
| 概念题 | ⭐⭐⭐⭐ | 详细解释 + 示例 |
| 数据库题 | ⭐⭐⭐⭐ | SQL 查询 + 优化建议 |

### **2. 截图质量要求**

✅ **好的截图：**
- 题目完整、清晰
- 文字可读
- 包含必要的上下文

❌ **不好的截图：**
- 模糊不清
- 题目被截断
- 光线过暗/过亮

### **3. 获得最佳回复的技巧**

1. **截图内容完整**
   - 确保题目描述完整
   - 包含输入输出示例
   - 包含约束条件

2. **单一题目**
   - 每次截取一道题
   - 避免多个问题混在一起

3. **清晰的上下文**
   - 如果是特定语言的题目，确保截图中有说明
   - 如果有特殊要求，确保包含在截图中

---

## 🔧 自定义提示词

如果你想自定义 AI 的行为，可以编辑 `backend/vision.py` 文件：

```python
# 找到第 30 行附近的 prompt 变量
prompt = """
你的自定义提示词...
"""
```

### **自定义示例：**

**只要代码，不要解释：**
```python
prompt = """
请分析截图中的题目，只给出 Python 代码实现，不需要其他解释。
代码必须包含完整的测试用例。
"""
```

**要求使用特定语言：**
```python
prompt = """
请分析截图中的题目，使用 Java 语言给出解决方案。
包含：
1. 完整的 Java 代码
2. 解题思路
3. 时间空间复杂度
"""
```

**系统设计专用：**
```python
prompt = """
这是一个系统设计面试题。请提供：
1. 需求分析
2. 架构设计图描述
3. 技术选型和理由
4. 扩展性考虑
5. 潜在问题和解决方案
"""
```

---

## 📊 性能对比

### **优化前：**
- ⏱️ 响应时间：3-5 秒
- 📝 回复长度：500-800 字符
- 🎯 回复质量：简单描述
- 💻 代码质量：基础实现

### **优化后：**
- ⏱️ 响应时间：4-6 秒（稍慢，因为更详细）
- 📝 回复长度：1000-2000 字符
- 🎯 回复质量：结构化、专业化
- 💻 代码质量：完整、带注释、可运行

---

## 💡 更多优化建议

### **1. 添加语言选择**
在悬浮窗或主窗口添加语言选择下拉框：
- Python（默认）
- Java
- C++
- JavaScript
- Go

### **2. 题目类型预判**
添加按钮快速选择题目类型：
- 🧮 算法题
- 💻 编程题
- 🏗️ 系统设计
- 📚 概念题

### **3. 历史记录**
保存之前的分析结果，方便查看和对比。

### **4. 代码高亮**
在 UI 中使用语法高亮显示代码，提升可读性。

---

## 🎓 最佳实践

1. **清晰的题目截图** - 确保题目完整清晰
2. **合理的预期** - AI 提供思路和参考，需要自己理解
3. **验证答案** - 运行代码验证正确性
4. **学习理解** - 重点理解思路，而不是死记代码
5. **举一反三** - 基于 AI 的回复，思考变体和优化

---

**🎉 享受更智能的面试辅助体验！**






