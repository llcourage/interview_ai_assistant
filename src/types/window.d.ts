// 全局 Window 接口类型声明

export interface AiShotAPI {
  /**
   * 监听截屏完成事件
   * @param callback 回调函数，接收 base64 编码的图片
   */
  onScreenshotTaken: (callback: (base64Image: string) => void) => void;

  /**
   * 监听发送截图请求事件
   * @param callback 回调函数，接收 base64 编码的图片
   */
  onSendScreenshotRequest: (callback: (base64Image: string) => void) => void;

  /**
   * 监听截图错误事件
   * @param callback 回调函数，接收错误消息
   */
  onScreenshotError: (callback: (errorMessage: string) => void) => void;

  /**
   * 手动触发截屏
   * @returns Promise，返回 base64 编码的图片
   */
  captureScreen: () => Promise<string>;

  /**
   * 发送图片到后端（保留接口，前端直接调用 HTTP API）
   * @param imageBase64 base64 编码的图片
   * @returns Promise
   */
  sendToBackend: (imageBase64: string) => Promise<{ success: boolean }>;

  /**
   * 最小化悬浮窗
   */
  minimizeOverlay: () => void;

  /**
   * 显示悬浮窗
   */
  showOverlay: () => void;

  /**
   * 调整悬浮窗大小
   * @param height 新的高度
   */
  resizeOverlay: (height: number) => void;

  /**
   * 移动悬浮窗 (Local Shortcut)
   * @param direction 方向 'up' | 'down' | 'left' | 'right'
   * @param step 步长
   */
  moveOverlay: (direction: 'up' | 'down' | 'left' | 'right', step?: number) => void;

  /**
   * 控制点击穿透
   * @param ignore true: 启用穿透, false: 禁用穿透
   */
  setIgnoreMouseEvents: (ignore: boolean) => void;

  /**
   * 打开主窗口
   */
  openMainWindow: () => void;

  /**
   * 移除事件监听器
   * @param channel 事件通道名称
   */
  removeListener: (channel: string) => void;
}

declare global {
  interface Window {
    aiShot: AiShotAPI;
  }
}

export {};

