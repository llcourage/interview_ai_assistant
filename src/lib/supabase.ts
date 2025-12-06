/**
 * @deprecated 此文件已废弃
 * 前端不再直接连接 Supabase，所有认证通过 Vercel API 进行
 * 请使用 src/lib/auth.ts 中的认证函数
 * 
 * 此文件保留仅为向后兼容，将在未来版本中移除
 */

// 导出 null 以避免导入错误
import { createClient } from '@supabase/supabase-js';

// Supabase 配置 - 从环境变量获取
// 注意：这些配置仅用于前端 OAuth 流程（exchangeCodeForSession）
// 其他所有操作都通过 Vercel API 进行
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://cjrblsalpfhugeatrhrr.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

if (!supabaseAnonKey) {
  console.warn('⚠️ VITE_SUPABASE_ANON_KEY 未设置，OAuth 功能可能无法正常工作');
}

// 创建 Supabase 客户端（仅用于前端 OAuth 流程）
export const supabase = createClient(supabaseUrl, supabaseAnonKey);






