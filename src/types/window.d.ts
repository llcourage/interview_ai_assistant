// Global Window interface type declaration

export interface AiShotAPI {
  /**
   * Listen to screenshot completion event
   * @param callback Callback function that receives base64 encoded image
   */
  onScreenshotTaken: (callback: (base64Image: string) => void) => void;

  /**
   * Listen to send screenshot request event
   * @param callback Callback function that receives base64 encoded image
   */
  onSendScreenshotRequest: (callback: (base64Image: string) => void) => void;

  /**
   * Listen to screenshot error event
   * @param callback Callback function that receives error message
   */
  onScreenshotError: (callback: (errorMessage: string) => void) => void;

  /**
   * Manually trigger screenshot
   * @returns Promise that returns base64 encoded image
   */
  captureScreen: () => Promise<string>;

  /**
   * Send image to backend (reserved interface, frontend directly calls HTTP API)
   * @param imageBase64 base64 encoded image
   * @returns Promise
   */
  sendToBackend: (imageBase64: string) => Promise<{ success: boolean }>;

  /**
   * Minimize overlay window
   */
  minimizeOverlay: () => void;

  /**
   * Show overlay window
   */
  showOverlay: () => void;

  /**
   * Resize overlay window
   * @param height New height
   */
  resizeOverlay: (height: number) => void;

  /**
   * Move overlay window (Local Shortcut)
   * @param direction Direction 'up' | 'down' | 'left' | 'right'
   * @param step Step size
   */
  moveOverlay: (direction: 'up' | 'down' | 'left' | 'right', step?: number) => void;

  /**
   * Control click-through
   * @param ignore true: Enable click-through, false: Disable click-through
   */
  setIgnoreMouseEvents: (ignore: boolean) => void;

  /**
   * Open main window
   */
  openMainWindow: () => void;

  /**
   * Listen to scroll event
   * @param callback Callback function that receives direction 'up' | 'down'
   */
  onScrollContent: (callback: (direction: 'up' | 'down') => void) => void;

  /**
   * Remove event listener
   * @param channel Event channel name
   */
  removeListener: (channel: string) => void;

  /**
   * User login/logout
   */
  userLoggedIn: () => Promise<{ success: boolean }>;
  userLoggedOut: () => Promise<{ success: boolean }>;

  /**
   * Local speech to text (using local Whisper)
   * @param audioData base64 encoded audio data
   * @param language Language code, default is 'zh'
   * @returns Promise that returns transcription result
   */
  speechToTextLocal?: (
    audioData: string,
    language?: string
  ) => Promise<{
    success: boolean;
    text: string;
    language: string;
    duration: number;
    error?: string;
  }>;

  /**
   * Get all scenes
   * @returns Promise that returns all scenes (built-in, general, custom)
   */
  getAllScenes?: () => Promise<{
    builtIn: any[];
    general: any;
    custom: any[];
  }>;

  /**
   * Select scene
   * @param sceneId Scene ID
   * @param presetId Preset ID
   * @returns Promise
   */
  selectScenario?: (sceneId: string, presetId: string) => Promise<{ success: boolean; prompt: string }>;

  /**
   * Notify that scene has been updated (refresh menu)
   */
  notifyScenarioUpdated?: () => void;

  /**
   * Listen to scene selection event
   * @param callback Callback function
   */
  onScenarioSelected?: (callback: (data: { sceneId: string; presetId: string; prompt: string }) => void) => void;

  /**
   * Listen to open scene editor event
   * @param callback Callback function
   */
  onOpenScenarioEditor?: (callback: (data: { mode: 'create' | 'edit'; scenario?: any }) => void) => void;

  /**
   * Google OAuth login (Electron only)
   * @returns Promise that returns object containing code
   */
  loginWithGoogle?: () => Promise<{ success: boolean; code?: string; error?: string }>;

  /**
   * Select folder (Electron only)
   * @param options Options, containing title and defaultPath
   * @returns Promise that returns object containing canceled and path
   */
  selectFolder?: (options?: { title?: string; defaultPath?: string }) => Promise<{ canceled: boolean; path: string | null; error?: string }>;

  /**
   * Show Token usage warning (Electron only)
   * @param message Warning message
   * @param usagePercentage Usage percentage
   */
  showTokenWarning?: (message: string, usagePercentage: string) => void;
}

declare global {
  interface Window {
    aiShot: AiShotAPI;
  }
}

export {};

