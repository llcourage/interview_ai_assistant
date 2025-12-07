/**
 * Supabase 客户端配置
 * 注意：此客户端仅用于前端 OAuth 流程（exchangeCodeForSession）
 * 其他所有操作都通过 Vercel API 进行
 * 
 * ⚠️ 此文件已废弃，不再导出 supabase 客户端
 * 所有 Supabase 客户端都在 handleOAuthCallback 中动态创建
 * 这样可以确保配置已从 API 获取
 * 
 * 保留此文件仅为向后兼容，避免导入错误
 */

// 不再导出任何内容，所有 Supabase 操作都在 auth.ts 中动态处理






