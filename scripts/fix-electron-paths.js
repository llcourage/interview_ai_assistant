/**
 * 修复 Electron 构建后的 HTML 文件中的绝对路径
 * 将 /assets/ 替换为 ./assets/ 以支持 file:// 协议
 */

const fs = require('fs');
const path = require('path');

const distIndexHtml = path.join(__dirname, '../dist/index.html');

if (!fs.existsSync(distIndexHtml)) {
  console.error('❌ dist/index.html 不存在，请先运行 npm run build');
  process.exit(1);
}

console.log('🔧 修复 Electron 资源路径...');

let html = fs.readFileSync(distIndexHtml, 'utf8');

// 将绝对路径替换为相对路径
// /assets/ -> ./assets/
html = html.replace(/href="\/assets\//g, 'href="./assets/');
html = html.replace(/src="\/assets\//g, 'src="./assets/');
html = html.replace(/href="\/favicon\.png"/g, 'href="./favicon.png"');

fs.writeFileSync(distIndexHtml, html, 'utf8');

console.log('✅ 路径修复完成！');
console.log('   已将 /assets/ 替换为 ./assets/');
console.log('   已将 /favicon.png 替换为 ./favicon.png');

