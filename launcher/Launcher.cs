using System;
using System.Diagnostics;
using System.IO;
using System.Threading;

namespace DesktopAI.Launcher
{
    class Program
    {
        static void Main()
        {
            try
            {
                // Get launcher directory
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                Console.WriteLine($"Launcher directory: {baseDir}");
                
                // Try multiple possible paths for backend.exe
                // 1. Same directory as launcher: backend/backend.exe
                // 2. Parent directory: ../backend/backend.exe (for test-launcher structure)
                // 3. Nested structure: backend/backend/backend.exe (onedir mode from dist)
                string[] possiblePaths = new string[]
                {
                    Path.Combine(baseDir, "backend", "backend.exe"),                    // release_root/backend/backend.exe
                    Path.Combine(Directory.GetParent(baseDir)?.FullName ?? "", "backend", "backend.exe"), // ../backend/backend.exe
                    Path.Combine(baseDir, "backend", "backend", "backend.exe"),         // dist/backend/backend/backend.exe (onedir mode)
                    Path.Combine(Directory.GetParent(baseDir)?.FullName ?? "", "backend", "backend", "backend.exe") // ../backend/backend/backend.exe
                };
                
                Console.WriteLine("Searching for backend.exe...");
                string? backendPath = null;
                foreach (string path in possiblePaths)
                {
                    Console.WriteLine($"  Checking: {path}");
                    if (File.Exists(path))
                    {
                        backendPath = path;
                        Console.WriteLine($"  ✅ Found: {path}");
                        break;
                    }
                }
                
                if (backendPath == null)
                {
                    Console.WriteLine("\n❌ Error: Cannot find backend.exe");
                    Console.WriteLine("\nSearched in:");
                    foreach (string path in possiblePaths)
                    {
                        Console.WriteLine($"  - {path}");
                    }
                    Console.WriteLine($"\nCurrent directory: {Environment.CurrentDirectory}");
                    Console.WriteLine($"Launcher directory: {baseDir}");
                    Console.WriteLine("\nPlease ensure backend.exe is in one of these locations:");
                    Console.WriteLine("  - backend/backend.exe (same directory as Launcher.exe)");
                    Console.WriteLine("  - ../backend/backend.exe (parent directory)");
                    Console.WriteLine("\nPress any key to exit...");
                    Console.ReadKey();
                    return;
                }

                Console.WriteLine("========================================");
                Console.WriteLine("Desktop AI");
                Console.WriteLine("========================================");
                Console.WriteLine($"Backend path: {backendPath}");
                Console.WriteLine("Starting backend service...");

                // Start backend process
                // Set working directory to backend.exe's directory
                string backendDir = Path.GetDirectoryName(backendPath) ?? baseDir;
                
                var backendProcess = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = backendPath,
                        WorkingDirectory = backendDir,  // Use backend.exe's directory
                        UseShellExecute = false,
                        CreateNoWindow = true,  // Hide backend console window
                        RedirectStandardOutput = true,
                        RedirectStandardError = true
                    }
                };

                backendProcess.Start();
                Console.WriteLine($"Backend process started (PID: {backendProcess.Id})");
                Console.WriteLine("Waiting for backend service to be ready...");

                // Wait for backend to start (2 seconds)
                Thread.Sleep(2000);

                // Start Electron client (similar to start-all.bat behavior)
                Console.WriteLine("Starting Electron client...");
                
                // Try to find electron.exe or use npm to start Electron
                string? electronPath = null;
                string[] possibleElectronPaths = new string[]
                {
                    Path.Combine(baseDir, "electron", "electron.exe"),
                    Path.Combine(Directory.GetParent(baseDir)?.FullName ?? "", "electron.exe"),
                    Path.Combine(Directory.GetParent(baseDir)?.FullName ?? "", "node_modules", ".bin", "electron.cmd"),
                    Path.Combine(baseDir, "node_modules", ".bin", "electron.cmd")
                };
                
                foreach (string path in possibleElectronPaths)
                {
                    if (File.Exists(path))
                    {
                        electronPath = path;
                        Console.WriteLine($"  ✅ Found Electron: {path}");
                        break;
                    }
                }
                
                Process? electronProcess = null;
                if (electronPath != null)
                {
                    // Found electron.exe, start it directly
                    string electronDir = Path.GetDirectoryName(electronPath) ?? baseDir;
                    electronProcess = new Process
                    {
                        StartInfo = new ProcessStartInfo
                        {
                            FileName = electronPath,
                            Arguments = "--desktop-mode",
                            WorkingDirectory = Directory.GetParent(baseDir)?.FullName ?? baseDir,
                            UseShellExecute = false,
                            CreateNoWindow = false,
                            Environment = { ["DESKTOP_MODE"] = "true" }
                        }
                    };
                    electronProcess.Start();
                    Console.WriteLine($"Electron process started (PID: {electronProcess.Id})");
                }
                else
                {
                    // Try to use npm to start Electron (requires Node.js)
                    Console.WriteLine("  ℹ️  Electron.exe not found, trying npm...");
                    string projectRoot = Directory.GetParent(baseDir)?.FullName ?? baseDir;
                    string packageJsonPath = Path.Combine(projectRoot, "package.json");
                    
                    if (File.Exists(packageJsonPath))
                    {
                        // Check if node_modules exists
                        string nodeModulesPath = Path.Combine(projectRoot, "node_modules");
                        if (Directory.Exists(nodeModulesPath))
                        {
                            // Use npm to start Electron
                            electronProcess = new Process
                            {
                                StartInfo = new ProcessStartInfo
                                {
                                    FileName = "npm",
                                    Arguments = "run dev",
                                    WorkingDirectory = projectRoot,
                                    UseShellExecute = false,
                                    CreateNoWindow = false,
                                    Environment = { ["DESKTOP_MODE"] = "true" }
                                }
                            };
                            electronProcess.Start();
                            Console.WriteLine($"npm run dev started (PID: {electronProcess.Id})");
                        }
                        else
                        {
                            Console.WriteLine("  ⚠️  node_modules not found. Please run 'npm install' first.");
                            Console.WriteLine("  Opening browser as fallback...");
                            Process.Start(new ProcessStartInfo
                            {
                                FileName = "http://127.0.0.1:8000",
                                UseShellExecute = true
                            });
                        }
                    }
                    else
                    {
                        Console.WriteLine("  ⚠️  package.json not found. Opening browser as fallback...");
                        Process.Start(new ProcessStartInfo
                        {
                            FileName = "http://127.0.0.1:8000",
                            UseShellExecute = true
                        });
                    }
                }

                Console.WriteLine("========================================");
                Console.WriteLine("✅ Startup complete!");
                Console.WriteLine("   Backend URL: http://127.0.0.1:8000");
                if (electronProcess != null)
                {
                    Console.WriteLine("   Electron client is running");
                }
                Console.WriteLine("========================================");
                Console.WriteLine("\n💡 Tips:");
                Console.WriteLine("   - Closing this window will stop all services");
                Console.WriteLine("   - Press Ctrl+C to exit safely");
                Console.WriteLine("========================================");

                // Wait for backend process to exit
                backendProcess.WaitForExit();
                
                // If Electron is running, terminate it when backend exits
                if (electronProcess != null && !electronProcess.HasExited)
                {
                    electronProcess.Kill();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Startup failed: {ex.Message}");
                Console.WriteLine("Press any key to exit...");
                Console.ReadKey();
            }
        }
    }
}

